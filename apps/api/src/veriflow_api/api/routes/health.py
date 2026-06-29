import asyncio

from fastapi import APIRouter, status
from fastapi.responses import JSONResponse

from veriflow_api.cache import check_redis
from veriflow_api.config import settings
from veriflow_api.database import check_database
from veriflow_api.schemas import LivenessResponse, ReadinessResponse

router = APIRouter()


@router.get("/health/live", response_model=LivenessResponse)
async def liveness() -> LivenessResponse:
    """Report whether the API process is running."""

    return LivenessResponse(
        status="healthy",
        service=settings.app_name,
        version=settings.api_version,
    )


@router.get(
    "/health/ready",
    response_model=ReadinessResponse,
    responses={status.HTTP_503_SERVICE_UNAVAILABLE: {"model": ReadinessResponse}},
)
async def readiness() -> ReadinessResponse | JSONResponse:
    """Verify that the API can reach its required infrastructure."""

    checks: dict[str, str] = {"database": "unhealthy", "redis": "unhealthy"}

    database_result, redis_result = await asyncio.gather(
        check_database(),
        check_redis(),
        return_exceptions=True,
    )

    if not isinstance(database_result, BaseException):
        checks["database"] = "healthy"
    if not isinstance(redis_result, BaseException):
        checks["redis"] = "healthy"

    all_healthy = all(value == "healthy" for value in checks.values())
    payload = ReadinessResponse(
        status="healthy" if all_healthy else "unhealthy",
        service=settings.app_name,
        version=settings.api_version,
        checks=checks,  # type: ignore[arg-type]
    )

    if all_healthy:
        return payload

    return JSONResponse(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        content=payload.model_dump(),
    )
