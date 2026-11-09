"""Request identity, mutation origin checks and safe unexpected error boundary."""
import os
from uuid import uuid4
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.exceptions import HTTPException
from .errors import response
from .logging import log_failure


class UploadBodyLimitMiddleware:
    """Bound transport bytes before multipart spooling, not only copied file bytes."""
    limits={'/api/v1/files':257*1024*1024,'/api/v1/definition-uploads':11*1024*1024}

    def __init__(self,app):self.app=app

    async def __call__(self,scope,receive,send):
        limit=self.limits.get(scope.get('path')) if scope['type']=='http' and scope.get('method')=='POST' else None
        if limit is None:return await self.app(scope,receive,send)
        request=Request(scope)
        declared=request.headers.get('content-length')
        if declared is not None:
            try:size=int(declared)
            except ValueError:size=-1
            if size<0:
                return await response(request,'INVALID_CONTENT_LENGTH','Invalid upload content length.',400)(scope,receive,send)
            if size>limit:
                return await response(request,'UPLOAD_BODY_TOO_LARGE','Upload exceeds the allowed size.',413)(scope,receive,send)
        consumed=0
        async def bounded_receive():
            nonlocal consumed
            message=await receive()
            if message['type']=='http.request':
                consumed+=len(message.get('body',b''))
                if consumed>limit:raise HTTPException(status_code=413)
            return message
        return await self.app(scope,bounded_receive,send)


class FoundationMiddleware(BaseHTTPMiddleware):
    async def dispatch(self,request,call_next):
        request.state.request_id=uuid4()
        if request.method not in ('GET','HEAD','OPTIONS') and request.url.path.startswith('/api/v1/'):
            allowed={s.strip() for s in os.environ.get('AAT_ALLOWED_ORIGINS','http://localhost:3000,http://127.0.0.1:3000').split(',')}
            origin=request.headers.get('origin')
            if request.headers.get('sec-fetch-site')=='cross-site' or origin is not None and origin not in allowed:
                return response(request,'ORIGIN_REJECTED','Request origin is not allowed.',403)
        try:
            result=await call_next(request)
        except Exception as exc:
            log_failure(request.state.request_id,exc)
            return response(request,'INTERNAL_ERROR','An unexpected error occurred.',500,True)
        result.headers['X-Request-ID']=str(request.state.request_id)
        return result
