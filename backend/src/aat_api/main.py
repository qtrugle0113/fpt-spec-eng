"""Liveness bootstrap; readiness sản phẩm được triển khai ở Phase 2."""

from fastapi import FastAPI

app = FastAPI(title="Airflow Automation Tool", docs_url=None, redoc_url=None)


@app.get("/api/v1/health/live")
def live() -> dict[str, str]:
    return {"status": "live", "stage": "bootstrap"}
