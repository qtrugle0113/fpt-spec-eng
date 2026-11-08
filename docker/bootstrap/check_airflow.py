"""Auth/API/UI Airflow thật; không in JWT hoặc password."""

import time
from pathlib import Path

import httpx


def check() -> None:
    with httpx.Client(base_url='http://airflow-apiserver:8080', timeout=5) as client:
        for _ in range(120):
            try:
                if client.get('/api/v2/monitor/health').status_code == 200:
                    break
            except httpx.HTTPError:
                pass
            time.sleep(1)
        else:
            raise RuntimeError('Airflow API did not become available')
        response = client.get('/api/v2/dags')
        assert response.status_code in (401, 403), 'Anonymous Airflow API must be rejected'
        response = client.post('/auth/token', json={
            'username': 'aat_service',
            'password': Path('/secrets/backend_secrets/airflow_service_password').read_text(),
        })
        assert response.status_code == 201 or response.status_code == 200, 'Service authentication failed'
        token = response.json()['access_token']
        assert client.get('/api/v2/dags', headers={'Authorization': f'Bearer {token}'}).status_code == 200
        assert client.get('/', follow_redirects=True).status_code == 200
    print('AIRFLOW_AUTH_API_UI_PASS')


if __name__ == '__main__':
    check()
