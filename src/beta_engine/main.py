"""FastAPI application entrypoint for the beta engine."""

from fastapi import FastAPI

from beta_engine.api.deps import build_runtime
from beta_engine.api.routes import router as api_router


def create_app(*, database_url: str | None = None) -> FastAPI:
    app = FastAPI(title="Squash Tour Beta Engine", version="0.1.0")
    app.state.runtime = build_runtime(database_url=database_url)
    app.include_router(api_router)
    return app


app = create_app()
