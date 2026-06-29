from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from veriflow_api.api.router import api_router
from veriflow_api.cache import redis_client
from veriflow_api.config import settings
from veriflow_api.database import engine
from veriflow_api.schemas import ServiceInfo


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    yield
    await redis_client.aclose()
    await engine.dispose()


app = FastAPI(
    title=settings.app_name,
    version=settings.api_version,
    description="Evidence, data, and decision intelligence API.",
    docs_url="/docs" if settings.app_env != "production" else None,
    redoc_url="/redoc" if settings.app_env != "production" else None,
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.backend_cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router)


@app.get("/", response_model=ServiceInfo, tags=["service"])
async def service_info() -> ServiceInfo:
    return ServiceInfo(
        name=settings.app_name,
        version=settings.api_version,
        environment=settings.app_env,
        docs_url="/docs" if settings.app_env != "production" else "disabled",
    )
