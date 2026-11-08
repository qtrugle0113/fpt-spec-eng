#!/bin/bash
set -euo pipefail
# Migration officielle uniquement; aucun SQL applicatif sur les tables Airflow.
airflow db migrate
airflow db check
echo 'Airflow migration complete; credentials suppressed'
