"""Khôi phục logical backup từ DB baseline cũ vào DB candidate, không đổi volume nguồn."""

import hashlib
import os
import subprocess
import unittest
import uuid


class DatabasePatchRestoreTests(unittest.TestCase):
    def test_old_sample_database_restores_into_candidate_namespace(self):
        source = os.environ['AAT_SOURCE_PROJECT']
        target = os.environ['AAT_COMPOSE_PROJECT']
        self.assertTrue(source.startswith('aat-phase1-'))
        self.assertTrue(target.startswith('aat-phase1-'))
        self.assertNotEqual(source, target)
        self.assertTrue(target.startswith('aat-phase1-t014-'))
        database = 'aat_patch_restore_' + uuid.uuid4().hex[:8]

        def execute(project, service, command, data=None):
            result = subprocess.run(
                [os.environ.get('PODMAN_BIN', 'podman'), 'exec', '-i',
                 f'{project}-{service}-1', 'sh', '-c', command],
                input=data, capture_output=True)
            # SQL backup và credentials không được in khi thất bại.
            self.assertEqual(result.returncode, 0, f'{service}: command exit {result.returncode}')
            return result.stdout

        pg = 'PGPASSWORD="$(cat /secrets/postgres_admin)" '
        mysql = 'MYSQL_PWD="$(cat /secrets/mysql_admin)" '
        self.assertIn(b'17.6', execute(source, 'postgres', pg + 'psql -h 127.0.0.1 -U postgres -Atc "SHOW server_version"'))
        self.assertIn(b'17.11', execute(target, 'postgres', pg + 'psql -h 127.0.0.1 -U postgres -Atc "SHOW server_version"'))
        self.assertIn(b'8.4.7', execute(source, 'mysql', mysql + 'mysql -uroot -N -e "SELECT VERSION()"'))
        self.assertIn(b'8.4.13', execute(target, 'mysql', mysql + 'mysql -uroot -N -e "SELECT VERSION()"'))

        pg_dump = execute(source, 'postgres', pg + 'pg_dump -h 127.0.0.1 -U postgres --no-owner --no-acl etl_test')
        my_dump = execute(source, 'mysql', mysql + 'mysqldump -uroot --single-transaction --set-gtid-purged=OFF --no-tablespaces etl_test')
        execute(target, 'postgres', pg + f'createdb -h 127.0.0.1 -U postgres {database}')
        execute(target, 'mysql', mysql + f'mysql -uroot -e "CREATE DATABASE {database}"')
        execute(target, 'postgres', pg + f'psql -h 127.0.0.1 -U postgres -v ON_ERROR_STOP=1 -d {database}', pg_dump)
        execute(target, 'mysql', mysql + f'mysql -uroot {database}', my_dump)

        for service, credentials, query in (
            ('postgres', pg, 'psql -h 127.0.0.1 -U postgres -At -d {database} -c "SELECT * FROM sample.customers_source ORDER BY customer_id"'),
            ('mysql', mysql, 'mysql -uroot -N {database} -e "SELECT * FROM customers_source ORDER BY customer_id"'),
        ):
            before = execute(source, service, credentials + query.format(database='etl_test'))
            after = execute(target, service, credentials + query.format(database=database))
            self.assertTrue(before)
            self.assertEqual(hashlib.sha256(before).digest(), hashlib.sha256(after).digest(), service)
