from fastapi import FastAPI
from fastapi.responses import JSONResponse


def create_app() -> FastAPI:
    app = FastAPI(
        title="BEPI",
        description="Unified space engineering platform",
        version="0.1.0",
    )

    @app.get("/health", tags=["system"])
    async def health() -> JSONResponse:
        return JSONResponse({"status": "ok"})

    from bepi.api.v1.router import router as v1_router
    app.include_router(v1_router, prefix="/api/v1")

    return app
