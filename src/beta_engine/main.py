"""FastAPI application entrypoint for the beta engine scaffold."""

from fastapi import FastAPI

from beta_engine.api.routes import router as api_router



def create_app() -> FastAPI:
    app = FastAPI(title="Squash Tour Beta Engine", version="0.1.0")
    app.include_router(api_router)
    return app


app = create_app()
