"""Bounded authenticated HTTP; command uncertainty is never hidden by replay."""
import base64
from datetime import datetime,timezone
from email.utils import parsedate_to_datetime
import json as json_module
import hashlib
from functools import lru_cache
from pathlib import Path
import threading
import time
from urllib.parse import quote,urlsplit
import httpx


def segment(value):return quote(str(value),safe='')


@lru_cache(maxsize=1)
def pinned_schema():
    root=Path(__file__).parent
    data=(root/'schema-3.3.2.json').read_bytes()
    provenance=json_module.loads((root/'schema-3.3.2.provenance.json').read_text())
    if hashlib.sha256(data).hexdigest()!=provenance['sha256'] or provenance['airflow_version']!='3.3.2':
        raise RuntimeError('Pinned Airflow API schema failed verification')
    return json_module.loads(data)


class AirflowError(Exception):
    def __init__(self,status,*,retryable=False):
        self.status=status;self.retryable=retryable
        messages={401:'Airflow authentication failed.',403:'Airflow access denied.',404:'Airflow resource not found.',
                  409:'Airflow command conflicts with an existing resource.',429:'Airflow rate limit exceeded.'}
        super().__init__(messages.get(status,'Airflow is unavailable or returned an invalid response.'))


class AirflowClient:
    def __init__(self,base_url,*,username,password,transport=None,sleep=None,clock=None):
        pinned_schema()
        parsed=urlsplit(base_url)
        if parsed.scheme not in ('http','https') or not parsed.hostname or parsed.username or parsed.password or parsed.query or parsed.fragment or parsed.path not in ('','/'):
            raise ValueError('An internal Airflow HTTP origin is required.')
        self.http=httpx.Client(base_url=base_url.rstrip('/'),transport=transport,trust_env=False,follow_redirects=False,
            timeout=httpx.Timeout(10,connect=3),headers={'Accept':'application/json'})
        self._username=username;self._password=password;self._token=None;self._expires=0
        self._auth_lock=threading.Lock();self._sleep=sleep or time.sleep;self._clock=clock or time.monotonic

    def __enter__(self):return self
    def __exit__(self,*_):self.close()
    def close(self):self.http.close();self._token=None;self._password=None

    def _exchange(self,deadline,*,force=False):
        with self._auth_lock:
            if not force and self._token and self._clock()<self._expires:return self._token
            remaining=deadline-self._clock()
            if remaining<=0:raise AirflowError(503,retryable=True)
            try:
                response=self.http.post('/auth/token',json={'username':self._username,'password':self._password},
                    timeout=httpx.Timeout(min(10,remaining/4),connect=min(3,remaining/4)))
                if response.status_code not in (200,201):raise AirflowError(response.status_code,retryable=response.status_code>=500)
                if len(response.content)>65536:raise AirflowError(503)
                token=response.json().get('access_token')
                if not isinstance(token,str) or not token or len(token)>32768:raise AirflowError(503)
            except (httpx.HTTPError,ValueError,TypeError,AttributeError):raise AirflowError(503,retryable=True) from None
            ttl=60
            try:
                encoded=token.split('.')[1];payload=json_module.loads(base64.urlsafe_b64decode(encoded+'='*(-len(encoded)%4)))
                ttl=max(0,min(86400,float(payload['exp'])-time.time()-30))
            except (ValueError,KeyError,TypeError,IndexError):pass
            self._token=token;self._expires=self._clock()+ttl
            return token

    def request(self,method,path,*,json=None,params=None):
        method=method.upper()
        if method not in ('GET','POST','PATCH') or not path.startswith('/') or path.startswith('//') or '?' in path or '#' in path:
            raise ValueError('A controlled Airflow API path and method are required.')
        deadline=self._clock()+30;refreshed=False
        attempts=3 if method=='GET' else 1
        for attempt in range(attempts):
            while True:
                token=self._exchange(deadline)
                remaining=deadline-self._clock()
                if remaining<=0:raise AirflowError(503,retryable=True)
                try:
                    with self.http.stream(method,'/api/v2'+path,json=json,params=params,headers={'Authorization':'Bearer '+token},
                        timeout=httpx.Timeout(min(10,remaining/4),connect=min(3,remaining/4))) as response:
                        status=response.status_code;retry_after=response.headers.get('Retry-After');body=bytearray()
                        for chunk in response.iter_bytes():
                            if len(body)+len(chunk)>2*1024**2 or self._clock()>=deadline:raise AirflowError(503,retryable=True)
                            body.extend(chunk)
                    if status==401 and not refreshed:
                        refreshed=True;self._exchange(deadline,force=True);continue
                    if 200<=status<300:
                        if status==204:return None
                        try:return json_module.loads(body)
                        except (ValueError,UnicodeError):raise AirflowError(503) from None
                    failure=AirflowError(status,retryable=status in (429,502,503,504))
                except httpx.HTTPError:
                    failure=AirflowError(503,retryable=True);retry_after=None
                break
            if method!='GET' or not failure.retryable or attempt+1==attempts:raise failure
            delay=2**attempt
            if retry_after:
                try:delay=max(0,float(retry_after))
                except ValueError:
                    try:delay=max(0,(parsedate_to_datetime(retry_after)-datetime.now(timezone.utc)).total_seconds())
                    except (ValueError,TypeError,OverflowError):raise failure from None
            if delay>=deadline-self._clock():raise failure
            self._sleep(delay)
        raise AirflowError(503,retryable=True)
