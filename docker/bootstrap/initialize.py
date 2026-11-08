"""Init local idempotent; Phase1 chưa tạo app metadata schema/migrations."""

import os
from pathlib import Path
import runpy


def initialize() -> None:
    for dirname in ('generated_dags', 'uploads', 'staging', 'airflow_logs'):
        path = Path('/data') / dirname
        path.mkdir(exist_ok=True, parents=True)
        os.chown(path, 50000, 50000)
        path.chmod(0o750)
    print('Bootstrap storage initialized; product schema not initialized (T030 required)')


if __name__ == '__main__':
    mode = os.environ.get('AAT_INIT_MODE', 'storage')
    if mode == 'databases':
        for database in ('postgres', 'mysql'):
            runpy.run_path(str(Path(__file__).parents[1] / database / 'initialize.py'), run_name='__main__')
    else:
        initialize()
