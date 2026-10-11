"""Restrict the account-free desktop preview to its own loopback origins."""

from starlette.responses import JSONResponse


class LunvriLocalMiddleware:
    def __init__(self, app, origins: list[str]):
        self.app = app
        self.origins = set(origins)
        self.hosts = {origin.removeprefix("http://") for origin in origins}

    async def __call__(self, scope, receive, send):
        if scope["type"] not in ("http", "websocket"):
            return await self.app(scope, receive, send)
        headers = {key.lower(): value.decode("latin-1") for key, value in scope["headers"]}
        origin = headers.get(b"origin")
        allowed = (
            headers.get(b"host") in self.hosts
            and (not origin or origin in self.origins)
            and headers.get(b"sec-fetch-site") != "cross-site"
        )
        if not allowed:
            if scope["type"] == "websocket":
                await send({"type": "websocket.close", "code": 1008})
            else:
                await JSONResponse({"detail": "A prévia Lunvri aceita somente acesso local."}, status_code=403)(
                    scope, receive, send
                )
            return
        await self.app(scope, receive, send)
