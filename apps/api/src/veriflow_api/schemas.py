from typing import Literal

from pydantic import BaseModel


class ServiceInfo(BaseModel):
    name: str
    version: str
    environment: str
    docs_url: str


class LivenessResponse(BaseModel):
    status: Literal["healthy"]
    service: str
    version: str


class ReadinessResponse(BaseModel):
    status: Literal["healthy", "unhealthy"]
    service: str
    version: str
    checks: dict[str, Literal["healthy", "unhealthy"]]
