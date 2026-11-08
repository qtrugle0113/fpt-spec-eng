FROM localhost/aat-airflow-pip263:0.1.0
RUN python -m pip install --no-cache-dir "apache-airflow==3.3.2" certifi==2026.10.18 urllib3==2.8.0 && python -m pip check && python -c "import airflow,airflow.sdk; assert airflow.__version__ == '3.3.2'"
