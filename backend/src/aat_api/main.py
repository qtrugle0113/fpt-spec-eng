"""Application routing; dependency-aware foundation readiness remains T034."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import os
from aat_api.routes.health import router as health_router
from aat_api.routes.operations import router as operations_router
from aat_api.errors import install_handlers
from aat_api.middleware import FoundationMiddleware

app = FastAPI(title="Airflow Automation Tool", docs_url=None, redoc_url=None)
install_handlers(app)
app.add_middleware(FoundationMiddleware)
app.add_middleware(CORSMiddleware,
    allow_origins=os.environ.get('AAT_ALLOWED_ORIGINS','http://localhost:3000,http://127.0.0.1:3000').split(','),
    allow_methods=['GET','POST','PATCH','DELETE','OPTIONS'],
    allow_headers=['Content-Type','If-Match','Idempotency-Key','X-Request-ID'],
    expose_headers=['ETag','Location','X-Request-ID'])


app.include_router(health_router, prefix='/api/v1')
app.include_router(operations_router,prefix='/api/v1')
