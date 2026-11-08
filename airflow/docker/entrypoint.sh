#!/bin/bash
set -euo pipefail
if [[ -f /secrets/airflow/airflow_db ]]; then
    export AIRFLOW__DATABASE__SQL_ALCHEMY_CONN="postgresql+psycopg://aat_airflow:$(cat /secrets/airflow/airflow_db)@postgres:5432/airflow_metadata"
    export AIRFLOW__API_AUTH__JWT_SECRET="$(cat /secrets/airflow/jwt_secret)"
    export AIRFLOW__CORE__FERNET_KEY="$(cat /secrets/airflow/fernet_key)"
    # SimpleAuth cần r+; dùng bản sao volatile riêng, nguồn persistent vẫn RO.
    umask 077
    cp /secrets/airflow/simple_auth_passwords.json /tmp/aat-simple-auth-passwords.json
    chmod 600 /tmp/aat-simple-auth-passwords.json
    export AIRFLOW__CORE__SIMPLE_AUTH_MANAGER_PASSWORDS_FILE=/tmp/aat-simple-auth-passwords.json
fi
if [[ "${1:-}" == "aat-initialize" ]]; then
    exec /bin/bash /opt/aat/initialize.sh
fi
exec /entrypoint "$@"
