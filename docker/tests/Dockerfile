FROM docker.io/library/python:3.12.16-slim-bookworm@sha256:0f086103b026048cc50cb5da25ec435c023c5241a83fc44daea593377abc61c4 AS wheels
RUN python -m pip install --no-cache-dir build==1.3.0 setuptools==80.9.0 wheel==0.45.1
WORKDIR /build
COPY packages/aat_metadata /build/packages/aat_metadata
COPY etl_engine /build/etl_engine
COPY backend /build/backend
RUN python -m build --wheel --no-isolation --outdir /wheels packages/aat_metadata && \
    python -m build --wheel --no-isolation --outdir /wheels etl_engine && \
    python -m build --wheel --no-isolation --outdir /wheels backend
FROM docker.io/library/python:3.12.16-slim-bookworm@sha256:0f086103b026048cc50cb5da25ec435c023c5241a83fc44daea593377abc61c4
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
COPY backend/requirements.lock /opt/aat/requirements.lock
RUN python -m pip install --no-cache-dir --require-hashes -r /opt/aat/requirements.lock
COPY --from=wheels /wheels /wheels
RUN python -m pip install --no-cache-dir --no-deps /wheels/*.whl && \
    groupadd --gid 50000 aat && useradd --uid 50000 --gid 50000 --create-home aat
COPY docker /opt/aat/docker
WORKDIR /opt/aat
USER root
RUN python -m pip install --no-cache-dir pytest==8.4.2 && python -m pip check
COPY tests /opt/aat/tests
COPY airflow/docker/build_constraints.py airflow/docker/constraints-policy.json airflow/docker/constraints-3.12.txt airflow/docker/overrides.lock /opt/aat/airflow/docker/
COPY samples /opt/aat/samples
COPY templates /opt/aat/templates
COPY specs/001-airflow-automation-tool/contracts/design-validation.json /opt/aat/specs/001-airflow-automation-tool/contracts/design-validation.json
COPY frontend/package.json /opt/aat/frontend/package.json
COPY backend/pyproject.toml /opt/aat/backend/pyproject.toml
COPY etl_engine/pyproject.toml /opt/aat/etl_engine/pyproject.toml
COPY packages/aat_metadata/pyproject.toml /opt/aat/packages/aat_metadata/pyproject.toml
COPY .gitattributes /opt/aat/.gitattributes
USER 50000:50000
CMD ["python", "-m", "pytest", "-p", "no:cacheprovider", "tests/unit", "-v"]
