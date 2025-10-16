from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
import time
import json

from .json_log_template import JsonLogTemplate


class Middleware(BaseHTTPMiddleware):


    def __init__(self, app):
        super().__init__(app)
        self.logger = JsonLogTemplate()


    async def dispatch(self, request: Request, call_next):


        request_start = time.time()
        method = request.method
        path = request.url.path

        response: Response = await call_next(request)

        duration_ms = int((time.time() - request_start) * 1000)
        status_code = response.status_code

        log_entry = self.logger.create_json(
            message=f"{method} {path} - Response {status_code}",
            service=path.split("/")[1],
            status=status_code
        )

        log_entry.update({
            "method": method,
            "path": path,
            "duration_ms": duration_ms
        })

        print(json.dumps(log_entry, indent=2))

        return response