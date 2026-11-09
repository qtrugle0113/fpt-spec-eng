"""Ten-minute HMAC scope confirmations, separate from persistent authorization."""
import base64
import hashlib
import hmac
import json
import time


class ConfirmationSigner:
    def __init__(self,key):
        if not isinstance(key,bytes) or len(key)<32:raise ValueError('Confirmation signing key unavailable')
        self.key=key

    def issue(self,scope,*,now=None):
        now=int(time.time() if now is None else now)
        payload=json.dumps({'scope':scope,'issued_at':now,'expires_at':now+600},sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()
        return base64.urlsafe_b64encode(payload).decode()+'.'+hmac.new(self.key,payload,hashlib.sha256).hexdigest()

    def verify(self,token,scope,*,now=None):
        try:
            if not isinstance(token,str) or len(token)>16384:raise ValueError()
            encoded,signature=token.split('.')
            payload=base64.b64decode(encoded,altchars=b'-_',validate=True)
            if not hmac.compare_digest(signature,hmac.new(self.key,payload,hashlib.sha256).hexdigest()):raise ValueError()
            data=json.loads(payload);clock=time.time() if now is None else now
            if set(data)!= {'scope','issued_at','expires_at'} or data['expires_at']-data['issued_at']!=600 or not data['issued_at']<=clock<data['expires_at'] or data['scope']!=scope:raise ValueError()
            return data['scope']
        except (ValueError,TypeError,KeyError,UnicodeError):raise ValueError('CONFIRMATION_STALE_OR_INVALID') from None
