from starlette.types import ASGIApp, Receive, Scope, Send


class SecurityHeadersMiddleware:
    def __init__(self, app: ASGIApp):
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send):
        async def send_wrapper(message):
            if message["type"] == "http.response.start":
                headers = dict(message.get("headers", []))

                def set_header(name: str, value: str):
                    headers[name.lower().encode()] = value.encode()

                # HSTS
                set_header(
                    "strict-transport-security",
                    "max-age=63072000; includeSubDomains; preload",
                )

                # X-Content-Type-Options
                set_header("x-content-type-options", "nosniff")

                # X-Frame-Options
                set_header("x-frame-options", "DENY")

                # Referrer-Policy
                set_header("referrer-policy", "strict-origin-when-cross-origin")

                # Permissions-Policy
                set_header(
                    "permissions-policy",
                    "geolocation=(), camera=(), microphone=()",
                )

                # Content-Security-Policy (CSP)
                csp = (
                    "default-src 'self'; "
                    "img-src 'self' data:; "
                    "style-src 'self' 'unsafe-inline'; "
                    "script-src 'self'; "
                    "object-src 'none'; "
                    "base-uri 'self'; "
                    "frame-ancestors 'none'"
                )
                set_header("content-security-policy", csp)

                # Cache-Control (for APIs)
                set_header(
                    "cache-control",
                    "no-store, max-age=0",
                )

                message["headers"] = list(headers.items())

            await send(message)

        await self.app(scope, receive, send_wrapper)