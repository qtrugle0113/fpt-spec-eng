FROM docker.io/library/python:3.12.16-slim-bookworm@sha256:0f086103b026048cc50cb5da25ec435c023c5241a83fc44daea593377abc61c4 AS wheels
RUN python -m pip install --no-cache-dir build==1.3.0 setuptools==84.2.1 wheel==0.46.2
WORKDIR /build
COPY packages/aat_metadata /build/packages/aat_metadata
COPY etl_engine /build/etl_engine
RUN python -m build --wheel --no-isolation --outdir /wheels packages/aat_metadata && \
    python -m build --wheel --no-isolation --outdir /wheels etl_engine
FROM docker.io/apache/airflow:slim-3.3.2-python3.12@sha256:8177d08e713886fe1cfc4d5e2683a72725756cd8086e57af8fe163ee76e2b82f AS security-patched
USER root
COPY airflow/docker/security/brotli.lock.json /opt/aat/security/brotli.lock.json
ADD https://security.debian.org/debian-security/pool/updates/main/b/brotli/libbrotli1_1.0.9-2+deb12u1_amd64.deb /opt/aat/security/libbrotli1.deb
COPY airflow/docker/install_security_patch.py /opt/aat/security/install_security_patch.py
RUN --network=none python /opt/aat/security/install_security_patch.py
COPY airflow/docker/os-packages.lock /opt/aat/os-packages.lock
RUN apt-get update && sed "/^#/d;/^$/d" /opt/aat/os-packages.lock | xargs apt-get install -y --no-install-recommends && rm -rf /var/lib/apt/lists/*
FROM security-patched AS runtime
COPY airflow/docker/constraints-3.12.txt airflow/docker/constraints-policy.json airflow/docker/build_constraints.py /opt/aat/
RUN python /opt/aat/build_constraints.py /opt/aat
USER airflow
COPY --chown=airflow:root airflow/docker/providers.lock /opt/aat/providers.lock
COPY --chown=airflow:root airflow/docker/overrides.lock /opt/aat/overrides.lock
COPY --chown=airflow:root etl_engine/requirements.lock /opt/aat/requirements.lock
COPY --from=wheels --chown=airflow:root /wheels/aat_metadata-0.1.0-py3-none-any.whl /wheels/aat_metadata-0.1.0-py3-none-any.whl
COPY --from=wheels --chown=airflow:root /wheels/aat_etl_engine-0.1.0-py3-none-any.whl /wheels/aat_etl_engine-0.1.0-py3-none-any.whl
RUN python -m pip install --no-cache-dir --require-hashes -r /opt/aat/overrides.lock -c /opt/aat/constraints-effective-3.12.txt && \
    python -m pip install --no-cache-dir --require-hashes --no-deps -r /opt/aat/providers.lock -c /opt/aat/constraints-effective-3.12.txt && \
    python -m pip install --no-cache-dir --require-hashes -r /opt/aat/requirements.lock -c /opt/aat/constraints-effective-3.12.txt && \
    python -m pip install --no-deps /wheels/*.whl && python -m pip check && \
    python -c "import airflow, airflow.sdk, aat_metadata, aat_etl; assert airflow.__version__ == '3.3.2'"
COPY --chown=airflow:root airflow/docker/entrypoint.sh /opt/aat/entrypoint.sh
COPY --chown=airflow:root airflow/docker/initialize.sh /opt/aat/initialize.sh
COPY --chown=airflow:root airflow/docker/airflow.cfg /opt/airflow/airflow.cfg
COPY --chown=airflow:root airflow/docker/health.sh /opt/aat/health.sh
COPY --chown=airflow:root docker/bootstrap/health.py /opt/aat/health.py
ENTRYPOINT ["/usr/bin/dumb-init", "--", "/bin/bash", "/opt/aat/entrypoint.sh"]

# LocalExecutor uses the local DAG volume, not Docker CLI or Git DAG bundles.
USER root
RUN apt-get purge -y docker-ce-cli git git-man rsync && \
    test ! -e /usr/bin/docker && test ! -e /usr/bin/git && test ! -e /usr/bin/rsync && \
    ! dpkg-query -W -f='${Status}' git git-man 2>/dev/null | grep -q 'install ok installed'
USER airflow

# uv extras and prek lint environment are not consumers of this LocalExecutor MVP.
RUN python -m pip uninstall -y uv && rm -rf /home/airflow/.local/share/uv/tools/prek && rm -f /home/airflow/.local/bin/prek && python -m pip check

COPY --chown=airflow:root airflow/docker/tooling.lock /opt/aat/tooling.lock
RUN python -m pip install --no-cache-dir --require-hashes --no-deps -r /opt/aat/tooling.lock && python -m pip check
