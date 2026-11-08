#!/bin/bash
set -euo pipefail
case "${1:-}" in
    api)
        export AAT_AIRFLOW_HEALTH_URL=http://127.0.0.1:8080/api/v2/monitor/health
        exec python /opt/aat/health.py airflow
        ;;
    scheduler)
        exec bash /opt/aat/entrypoint.sh jobs check --job-type SchedulerJob --hostname "${HOSTNAME}"
        ;;
    dag-processor)
        exec bash /opt/aat/entrypoint.sh jobs check --job-type DagProcessorJob --hostname "${HOSTNAME}"
        ;;
    *) exit 2 ;;
esac
