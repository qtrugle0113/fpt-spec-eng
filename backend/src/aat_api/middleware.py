"""Request identity, mutation origin checks and safe unexpected error boundary."""
import os
from uuid import uuid4
from starlette.middleware.base import BaseHTTPMiddleware
from .errors import response
from .logging import log_failure


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
