"""Binary drop-UID đã vá vẫn giữ hành vi server/entrypoint; không dùng volume thật."""

import os
import subprocess
import unittest


class DatabaseImageHardeningTests(unittest.TestCase):
    def run_image(self, image, *args):
        return subprocess.run(
            [os.environ.get('PODMAN_BIN', 'podman'), 'run', '--rm',
             '--entrypoint', '/bin/sh', image, '-c', *args],
            text=True, capture_output=True)

    def test_gosu_rebuilt_with_patched_go_preserves_drop_uid(self):
        for image, user in (
            (os.environ.get('AAT_PG_IMAGE', 'localhost/aat-postgres:17.11'), 'postgres'),
            (os.environ.get('AAT_MYSQL_IMAGE', 'localhost/aat-mysql:8.4.13'), 'mysql'),
        ):
            result = self.run_image(image, '/usr/local/bin/gosu --version')
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn('1.19 (go1.27.3 ', result.stdout)
            result = self.run_image(image, f'test "$(id -u {user})" = "$(gosu {user} id -u)" && test "$(gosu {user} id -u)" != 0')
            self.assertEqual(result.returncode, 0, result.stderr)

    def test_mysql_shell_removed_without_removing_server_or_client(self):
        image = os.environ.get('AAT_MYSQL_IMAGE', 'localhost/aat-mysql:8.4.13')
        result = self.run_image(image, 'test ! -e /usr/bin/mysqlsh && ! rpm -q mysql-shell && mysql --version && mysqld --version')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('8.4.13', result.stdout)
