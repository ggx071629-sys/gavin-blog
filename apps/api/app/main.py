from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.exception_handlers import http_exception_handler, request_validation_exception_handler
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from .config import Settings, get_settings
from .content_write_fence import content_write_fence
from .db import Database
from .http_errors import ApiException
from .media import LocalMediaStorage
from .routes import (
    admin_about,
    admin_articles,
    admin_assistant,
    admin_books,
    admin_content,
    admin_profile,
    admin_projects,
    admin_publishing,
    admin_taxonomy,
    auth,
    media,
    public_about,
    public_articles,
    public_books,
    public_profile,
    public_projects,
    public_search,
    public_taxonomy,
)
from .security import AdminPassword, LoginRateLimiter


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or get_settings()
    settings.validate_runtime()
    database = Database(settings.database_url)

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        app.state.content_write_lock = asyncio.Lock()
        app.state.assistant = None
        if settings.assistant_online_enabled:
            from .assistant.runtime import start_assistant_online, stop_assistant_online

            app.state.assistant = await start_assistant_online(settings, database)
            if settings.assistant_test_startup_bootstrap:
                from .assistant.test_bootstrap import bootstrap_test_assistant

                bootstrap_test_assistant(settings, database, app.state.assistant)
            if settings.assistant_local_dev_mode:
                from .assistant.development import bootstrap_development_assistant

                bootstrap_development_assistant(settings, database, app.state.assistant)
        yield
        assistant = getattr(app.state, "assistant", None)
        if assistant is not None:
            from .assistant.runtime import stop_assistant_online

            await stop_assistant_online(assistant)

    app = FastAPI(
        title="Gavin API",
        version="0.1.0",
        description="Content publishing and administration API for Gavin.",
        lifespan=lifespan,
    )
    app.state.settings = settings
    app.state.database = database
    app.state.media_storage = LocalMediaStorage(Path(settings.media_root))
    app.state.admin_password = AdminPassword(settings)
    app.state.login_limiter = LoginRateLimiter(
        settings.login_limit,
        settings.login_window_seconds,
    )
    app.state.content_write_lock = None
    app.state.assistant = None

    @app.middleware("http")
    async def fence_content_mutations(request: Request, call_next):
        if request.method not in {"POST", "PUT", "PATCH", "DELETE"}:
            return await call_next(request)
        # These operations mutate only the independent assistant runtime. In
        # particular, revocation must remain possible during content maintenance.
        # Questions and management writes still require the content backup fence.
        runtime_only = {
            ("POST", "/api/v1/assistant/sessions"),
            ("DELETE", "/api/v1/assistant/session"),
            ("POST", "/api/v1/admin/assistant/trial/sessions"),
            ("DELETE", "/api/v1/admin/assistant/trial/session"),
            ("POST", "/api/v1/admin/assistant/emergency-stop"),
        }
        if (request.method, request.url.path.rstrip("/")) in runtime_only:
            return await call_next(request)
        from .assistant.errors import AssistantOwnerLockError

        process_lock = request.app.state.content_write_lock
        if process_lock is None:
            return JSONResponse(
                status_code=503,
                content={"detail": "content write coordinator is unavailable"},
                headers={"Retry-After": "5", "Cache-Control": "no-store"},
            )
        async with process_lock:
            lock = content_write_fence(settings)
            try:
                lock.acquire()
            except AssistantOwnerLockError:
                return JSONResponse(
                    status_code=503,
                    content={"detail": "content writes are temporarily fenced"},
                    headers={"Retry-After": "5", "Cache-Control": "no-store"},
                )
            try:
                return await call_next(request)
            finally:
                lock.release()

    @app.exception_handler(ApiException)
    async def handle_api_exception(request, exc: ApiException) -> JSONResponse:
        headers = dict(exc.headers)
        if str(request.url.path).startswith(("/api/v1/assistant", "/api/v1/admin/assistant")):
            headers.setdefault("Cache-Control", "no-store")
        if exc.retry_after is not None:
            headers["Retry-After"] = str(exc.retry_after)
        return JSONResponse(
            status_code=exc.status_code,
            content={"error": {"code": exc.code, "message": exc.message}},
            headers=headers,
        )

    @app.exception_handler(HTTPException)
    async def handle_http_exception(request, exc: HTTPException):
        if str(request.url.path).startswith("/api/v1/admin/assistant"):
            code = "admin_auth_required" if exc.status_code == 401 else "admin_csrf_failed"
            if exc.status_code not in {401, 403}:
                code = "invalid_request"
            return JSONResponse(
                status_code=exc.status_code,
                content={"error": {"code": code, "message": "Admin request was rejected."}},
                headers={"Cache-Control": "no-store"},
            )
        return await http_exception_handler(request, exc)

    @app.exception_handler(RequestValidationError)
    async def handle_validation_exception(request, exc: RequestValidationError):
        if str(request.url.path).startswith("/api/v1/admin/assistant"):
            return JSONResponse(
                status_code=400,
                content={
                    "error": {
                        "code": "invalid_request",
                        "message": "Admin request is invalid.",
                    }
                },
                headers={"Cache-Control": "no-store"},
            )
        return await request_validation_exception_handler(request, exc)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.allowed_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=[
            "Content-Type",
            "X-CSRF-Token",
            "X-Assistant-CSRF",
            "Idempotency-Key",
            "Last-Event-ID",
        ],
        expose_headers=["Retry-After"],
    )
    app.include_router(auth.router, prefix="/api/v1")
    from .routes import account as account_routes

    app.include_router(account_routes.router, prefix="/api/v1")

    @app.middleware("http")
    async def private_auth_responses(request: Request, call_next):
        response = await call_next(request)
        if request.url.path.startswith("/api/v1/auth/"):
            response.headers["Cache-Control"] = "no-store"
        return response
    app.include_router(public_about.router, prefix="/api/v1")
    app.include_router(admin_about.router, prefix="/api/v1")
    app.include_router(admin_articles.router, prefix="/api/v1")
    app.include_router(admin_assistant.router, prefix="/api/v1")
    app.include_router(admin_taxonomy.router, prefix="/api/v1")
    app.include_router(admin_projects.router, prefix="/api/v1")
    app.include_router(admin_books.router, prefix="/api/v1")
    app.include_router(admin_content.router, prefix="/api/v1")
    app.include_router(admin_publishing.router, prefix="/api/v1")
    app.include_router(media.router, prefix="/api/v1")
    app.include_router(public_articles.router, prefix="/api/v1")
    app.include_router(public_taxonomy.router, prefix="/api/v1")
    app.include_router(public_projects.router, prefix="/api/v1")
    app.include_router(public_books.router, prefix="/api/v1")
    app.include_router(public_search.router, prefix="/api/v1")
    app.include_router(public_profile.router, prefix="/api/v1")
    app.include_router(admin_profile.router, prefix="/api/v1")
    from .assistant.routes import router as assistant_router

    app.include_router(assistant_router, prefix="/api/v1")

    @app.get("/api/health", tags=["health"])
    def health() -> dict[str, str]:
        return {"status": "ok"}

    return app
