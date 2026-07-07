from fastapi import APIRouter

from app.schemas.domain.health import HealthResponse
from app.schemas.response import ApiResponse

router = APIRouter()


@router.get("/health", response_model=ApiResponse[HealthResponse])
def health_check() -> ApiResponse[HealthResponse]:
    return ApiResponse(data=HealthResponse(status="UP"))
