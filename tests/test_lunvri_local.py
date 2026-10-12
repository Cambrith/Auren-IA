import unittest

from open_webui.utils.lunvri_local import LunvriLocalMiddleware


class LocalPreviewTests(unittest.IsolatedAsyncioTestCase):
    async def run_request(self, host, origin=None, fetch_site=None, scope_type='http'):
        events = []
        called = []

        async def app(scope, receive, send):
            called.append(True)

        async def send(event):
            events.append(event)

        async def receive():
            return {'type': 'http.request'}

        headers = [(b'host', host.encode())]
        if origin:
            headers.append((b'origin', origin.encode()))
        if fetch_site:
            headers.append((b'sec-fetch-site', fetch_site.encode()))
        middleware = LunvriLocalMiddleware(app, ['http://127.0.0.1:8175', 'http://127.0.0.1:5179'])
        await middleware({'type': scope_type, 'headers': headers}, receive, send)
        return called, events

    async def test_own_origin_and_backend_client_work(self):
        for origin in (None, 'http://127.0.0.1:8175', 'http://127.0.0.1:5179'):
            called, _ = await self.run_request('127.0.0.1:8175', origin)
            self.assertTrue(called)

    async def test_cross_origin_cross_site_and_wrong_host_are_blocked(self):
        for host, origin, site in [
            ('evil.example', None, None),
            ('127.0.0.1:8175', 'https://evil.example', None),
            ('127.0.0.1:8175', None, 'cross-site'),
        ]:
            called, events = await self.run_request(host, origin, site)
            self.assertFalse(called)
            self.assertEqual(events[0]['status'], 403)

    async def test_unauthorized_websocket_is_closed(self):
        called, events = await self.run_request('127.0.0.1:8175', 'https://evil.example', scope_type='websocket')
        self.assertFalse(called)
        self.assertEqual(events[0], {'type': 'websocket.close', 'code': 1008})


if __name__ == '__main__':
    unittest.main()
