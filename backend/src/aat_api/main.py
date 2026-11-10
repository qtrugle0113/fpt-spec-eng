"""Application routing; dependency-aware foundation readiness remains T034."""

from fastapi import FastAPI
from contextlib import asynccontextmanager
from fastapi.middleware.cors import CORSMiddleware
import os
from aat_api.routes.health import router as health_router
from aat_api.routes.operations import router as operations_router
from aat_api.routes.connections import router as connections_router
from aat_api.routes.templates import router as templates_router
from aat_api.routes.definition_uploads import router as definition_uploads_router
from aat_api.routes.tables import router as tables_router
from aat_api.routes.table_history import router as table_history_router
from aat_api.routes.files import router as files_router
from aat_api.routes.file_parsers import router as file_parsers_router
from aat_api.routes.runtime import router as runtime_router
from aat_api.routes.replacement_authorizations import router as authorizations_router
from aat_api.routes.dag_control import router as dag_control_router
from aat_api.routes.dag_builder import router as dag_builder_router
from aat_api.routes.monitoring import router as monitoring_router
from aat_api.routes.dashboard import router as dashboard_router
from aat_api.routes.settings import router as settings_router
from aat_api.errors import install_handlers
from aat_api.middleware import FoundationMiddleware,UploadBodyLimitMiddleware

@asynccontextmanager
async def lifespan(app):
    try:yield
    finally:
        from aat_api.services.runtime_binding import close_airflow
        close_airflow()


app = FastAPI(title="Airflow Automation Tool", docs_url=None, redoc_url=None,lifespan=lifespan)
install_handlers(app)
app.add_middleware(UploadBodyLimitMiddleware)
app.add_middleware(FoundationMiddleware)
app.add_middleware(CORSMiddleware,
    allow_origins=os.environ.get('AAT_ALLOWED_ORIGINS','http://localhost:3000,http://127.0.0.1:3000').split(','),
    allow_methods=['GET','POST','PATCH','DELETE','OPTIONS'],
    allow_headers=['Content-Type','If-Match','Idempotency-Key','X-Request-ID'],
    expose_headers=['ETag','Location','X-Request-ID'])


app.include_router(health_router, prefix='/api/v1')
app.include_router(operations_router,prefix='/api/v1')
app.include_router(connections_router,prefix='/api/v1')
app.include_router(templates_router,prefix='/api/v1')
app.include_router(definition_uploads_router,prefix='/api/v1')
app.include_router(tables_router,prefix='/api/v1')
app.include_router(table_history_router,prefix='/api/v1')
app.include_router(files_router,prefix='/api/v1')
app.include_router(file_parsers_router,prefix='/api/v1')
app.include_router(runtime_router)
app.include_router(authorizations_router,prefix='/api/v1')
app.include_router(dag_control_router,prefix='/api/v1')
app.include_router(dag_builder_router,prefix='/api/v1')
app.include_router(monitoring_router,prefix='/api/v1')
app.include_router(dashboard_router,prefix='/api/v1')
app.include_router(settings_router,prefix='/api/v1')
