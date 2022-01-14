from starlette.requests import Request
from starlette.middleware.base import BaseHTTPMiddleware

class RootPathMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, root_path_header: str = "X-Root-Path"):
        super().__init__(app)
        self.root_path_header = root_path_header
    async def dispatch(self, request: Request, call_next):
        if (root_path := request.headers.get("X-Root-Path")) is not None:
            scope = request.scope
            url = request.url
            root_path = root_path.removesuffix("/")
            root_path = f"{scope.get('root_path', '')}{root_path}"
            request._url = url.replace(path=f"{root_path}{url.path}")
            scope["root_path"] = root_path
            # scope["path"] = root_path + scope["path"]  # Could need in future
        return await call_next(request)
