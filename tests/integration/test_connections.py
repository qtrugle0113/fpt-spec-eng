"""T036: actual PostgreSQL/MySQL probes and isolated DNS-policy negative controls."""
import importlib
import os
import socket
import threading
import time
import unittest
from unittest.mock import patch
from urllib.parse import urlparse,unquote
from uuid import uuid4


def required(name):
    try:return importlib.import_module(name)
    except ModuleNotFoundError as exc:
        if name.startswith(exc.name):raise AssertionError('Connections implementation missing: '+name) from None
        raise


class ConnectionAdapterTests(unittest.TestCase):
    def setUp(self):
        if os.environ.get('AAT_FOUNDATION_DISPOSABLE')!='1':raise RuntimeError('Disposable database required')
        self.pg=required('aat_api.services.connections.postgres')
        self.mysql=required('aat_api.services.connections.mysql')
        self.policy=required('aat_api.services.connections.policy')
        parsed=urlparse(os.environ['AAT_FOUNDATION_TEST_DSN'])
        self.password=unquote(parsed.password)
        self.pg_config=dict(host='postgres',port=5432,database_name='app_metadata',schema_name='public',username='postgres')
        self.mysql_config=dict(host='mysql',port=3306,database_name='etl_test',schema_name=None,username='aat_test')

    def check(self,adapter,config,password,status,code=None):
        started=time.monotonic()
        result=adapter.test_connection(config,password)
        self.assertLess(time.monotonic()-started,30,'Connection probe exceeded contract timeout')
        self.assertEqual(result.status,status)
        if code:self.assertEqual(result.code,code)
        self.assertTrue(password not in repr(result),'Probe result exposed password')
        self.assertTrue('postgresql://' not in repr(result),'Probe result exposed DSN')
        return result

    def test_postgres_success_auth_database_schema_and_closed_port(self):
        result=self.check(self.pg,self.pg_config,self.password,'SUCCESS')
        self.assertRegex(result.server_fingerprint,r'^[a-f0-9]{64}$')
        self.check(self.pg,self.pg_config,'wrong_'+uuid4().hex,'FAILED','AUTHENTICATION_FAILED')
        self.check(self.pg,dict(self.pg_config,database_name='missing_'+uuid4().hex),self.password,'FAILED','DATABASE_NOT_FOUND')
        self.check(self.pg,dict(self.pg_config,schema_name='missing_'+uuid4().hex),self.password,'FAILED','SCHEMA_NOT_FOUND')
        self.check(self.pg,dict(self.pg_config,port=65432),self.password,'FAILED','PORT_UNREACHABLE')

    def test_mysql_success_auth_database_and_closed_port(self):
        result=self.check(self.mysql,self.mysql_config,self.password,'SUCCESS')
        self.assertRegex(result.server_fingerprint,r'^[a-f0-9]{64}$')
        self.check(self.mysql,self.mysql_config,'wrong_'+uuid4().hex,'FAILED','AUTHENTICATION_FAILED')
        # Limited users may receive 1044 before the server discloses DB existence.
        self.check(self.mysql,dict(self.mysql_config,database_name='missing_'+uuid4().hex),self.password,'FAILED','PERMISSION_DENIED')
        self.check(self.mysql,dict(self.mysql_config,username='root',database_name='missing_'+uuid4().hex),self.password,'FAILED','DATABASE_NOT_FOUND')
        self.check(self.mysql,dict(self.mysql_config,port=65432),self.password,'FAILED','PORT_UNREACHABLE')

    def test_policy_rejects_url_path_metadata_and_unapproved_hosts(self):
        for host in ['postgresql://user:pass@postgres','../../secrets','169.254.169.254','127.0.0.1','unapproved.invalid']:
            with self.subTest(host=host),self.assertRaises(ValueError):self.policy.resolve_host(host,5432)

    def test_resolved_addresses_are_pinned_and_loopback_rebinding_rejected(self):
        # Isolated policy test; actual DB acceptance is covered above.
        address=(socket.AF_INET,socket.SOCK_STREAM,6,'',('10.89.0.25',5432))
        with patch('socket.getaddrinfo',return_value=[address]) as lookup:
            self.assertEqual(self.policy.resolve_host('postgres',5432),['10.89.0.25'])
            self.assertEqual(lookup.call_count,1)
        malicious=(socket.AF_INET,socket.SOCK_STREAM,6,'',('127.0.0.1',5432))
        with patch('socket.getaddrinfo',return_value=[address,malicious]),self.assertRaises(ValueError):
            self.policy.resolve_host('postgres',5432)

    def test_dns_failure_has_safe_bounded_result(self):
        with patch.dict(os.environ,{'AAT_DB_ALLOWED_HOSTS':'postgres,mysql,missing.invalid'}):
            self.check(self.pg,dict(self.pg_config,host='missing.invalid'),self.password,'FAILED','HOST_UNREACHABLE')

    def test_postgres_handshake_timeout_is_bounded_without_mocking_driver(self):
        self.handshake_timeout(self.pg,self.pg_config)

    def test_mysql_handshake_timeout_is_bounded_without_mocking_driver(self):
        self.handshake_timeout(self.mysql,self.mysql_config)

    def handshake_timeout(self,adapter,config):
        listener=socket.socket();listener.bind(('0.0.0.0',0));listener.listen(1);listener.settimeout(15)
        self.addCleanup(listener.close)
        stop=threading.Event()
        def hold():
            try:
                connection,_=listener.accept()
                with connection:stop.wait(15)
            except OSError:pass
        thread=threading.Thread(target=hold,daemon=True);thread.start()
        host=socket.gethostname()
        try:
            with patch.dict(os.environ,{'AAT_DB_ALLOWED_HOSTS':host}):
                self.check(adapter,dict(config,host=host,port=listener.getsockname()[1]),self.password,'FAILED','TIMEOUT')
        finally:stop.set();thread.join(timeout=2)
