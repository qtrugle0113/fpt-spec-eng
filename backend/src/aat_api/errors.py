"""Safe English error envelopes; raw dependency errors never leave this module."""
from uuid import uuid4
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException
from aat_api.schemas.common import ErrorBody,ErrorResponse,Issue
from aat_metadata.repositories.revisions import StaleRevision


class APIError(Exception):
    def __init__(self,code,message,status=409,retryable=False):
        self.code=code;self.message=message;self.status=status;self.retryable=retryable


def response(request,code,message,status,retryable=False,details=None):
    request_id=getattr(request.state,'request_id',uuid4())
    body=ErrorResponse(error=ErrorBody(code=code,message=message,request_id=request_id,retryable=retryable,details=details or []))
    return JSONResponse(status_code=status,content=body.model_dump(mode='json',exclude_none=True),headers={'X-Request-ID':str(request_id)})


def install_handlers(app):
    @app.exception_handler(StaleRevision)
    async def stale_revision(request,exc):return response(request,'REVISION_MISMATCH','Resource revision changed.',412)
    @app.exception_handler(APIError)
    async def api_error(request,exc):return response(request,exc.code,exc.message,exc.status,exc.retryable)

    @app.exception_handler(HTTPException)
    async def http_error(request,exc):
        messages={404:'Resource not found.',405:'Method not allowed.',401:'Authentication required.',403:'Access denied.'}
        return response(request,'HTTP_'+str(exc.status_code),messages.get(exc.status_code,'Request failed.'),exc.status_code)

    @app.exception_handler(RequestValidationError)
    async def validation_error(request,exc):
        # Only declared contract field names are reflected; never input values,
        # arbitrary extra keys, raw parser messages or exception context.
        safe={'path','query','body','id','limit','offset','default_batch_size','dashboard_refresh_interval',
              'default_timezone','staging_retention_days','acknowledged','allow_empty','confirmation_token'}
        details=[]
        for error in exc.errors()[:20]:
            location='.'.join(str(part) for part in error['loc'] if part in safe)
            details.append(Issue(scope='resource',code='INVALID_FIELD',message='Invalid request field.',column_name=location or None))
        return response(request,'VALIDATION_ERROR','Request validation failed.',422,details=details)
