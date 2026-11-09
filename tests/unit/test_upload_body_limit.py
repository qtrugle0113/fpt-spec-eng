"""Bound actual upload ingress before multipart spooling, including chunked bodies."""
import asyncio
import importlib
import json
import unittest
from uuid import uuid4
from starlette.exceptions import HTTPException


class UploadBodyLimitTests(unittest.TestCase):
    def setUp(self):
        module=importlib.import_module('aat_api.middleware')
        if not hasattr(module,'UploadBodyLimitMiddleware'):raise AssertionError('Upload ingress limit is not implemented')
        self.middleware=module.UploadBodyLimitMiddleware

    def test_declared_oversize_is_rejected_before_consuming_any_body(self):
        async def exercise():
            messages=[]
            async def app(*args):raise AssertionError('Oversize upload reached multipart parsing')
            async def receive():raise AssertionError('Oversize declared body was consumed')
            async def send(message):messages.append(message)
            identity=uuid4()
            scope=dict(type='http',method='POST',path='/api/v1/files',headers=[(b'content-length',str(257*1024*1024+1).encode())],state={'request_id':identity})
            await self.middleware(app)(scope,receive,send)
            self.assertEqual(messages[0]['status'],413)
            self.assertEqual(json.loads(messages[1]['body'])['error']['request_id'],str(identity))
        asyncio.run(exercise())

    def test_chunked_quota_does_not_forward_excess_or_buffer_whole_upload(self):
        async def exercise(path,limit):
            remaining=limit+65537;received=0;forwarded=0;messages=[]
            async def receive():
                nonlocal remaining,received
                size=min(65536,remaining);remaining-=size;received+=size
                return dict(type='http.request',body=b'x'*size,more_body=remaining>0)
            async def send(message):messages.append(message)
            async def app(scope,guarded_receive,send):
                nonlocal forwarded
                try:
                    while True:
                        message=await guarded_receive();forwarded+=len(message['body'])
                        if not message.get('more_body'):break
                    status=204
                except HTTPException as error:status=error.status_code
                await send(dict(type='http.response.start',status=status,headers=[]))
                await send(dict(type='http.response.body',body=b''))
            scope=dict(type='http',method='POST',path=path,headers=[],state={'request_id':uuid4()})
            await self.middleware(app)(scope,receive,send)
            self.assertEqual(messages[0]['status'],413)
            self.assertLessEqual(forwarded,limit);self.assertLessEqual(received,limit+65536)
            self.assertGreater(remaining,0)
        for path,limit in [('/api/v1/files',257*1024*1024),('/api/v1/definition-uploads',11*1024*1024)]:
            with self.subTest(path=path):asyncio.run(exercise(path,limit))
