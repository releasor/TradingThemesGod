"""模型服务配置 API。"""

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.schemas.model_provider import (
    ModelListResponse,
    ModelProviderResponse,
    ModelProviderUpsert,
    ModelTestResponse,
)
from app.services.model_provider import ModelProviderService

router = APIRouter(prefix="/model-providers", tags=["model-providers"])


@router.get("", response_model=list[ModelProviderResponse])
async def list_model_providers(db: AsyncSession = Depends(get_db)):
    return await ModelProviderService(db).list()


@router.post("", response_model=ModelProviderResponse, status_code=201)
async def create_model_provider(payload: ModelProviderUpsert, db: AsyncSession = Depends(get_db)):
    return await ModelProviderService(db).save(payload)


@router.put("/{provider_id}", response_model=ModelProviderResponse)
async def update_model_provider(provider_id: int, payload: ModelProviderUpsert, db: AsyncSession = Depends(get_db)):
    return await ModelProviderService(db).save(payload, provider_id)


@router.delete("/{provider_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_model_provider(provider_id: int, db: AsyncSession = Depends(get_db)):
    await ModelProviderService(db).delete(provider_id)
    return Response(status_code=204)


@router.post("/{provider_id}/test", response_model=ModelTestResponse)
async def test_model_provider(provider_id: int, db: AsyncSession = Depends(get_db)):
    text, latency = await ModelProviderService(db).test(provider_id)
    return ModelTestResponse(success=True, message=text[:200] or "连接成功", latency_ms=latency)


@router.get("/{provider_id}/models", response_model=ModelListResponse)
async def list_provider_models(provider_id: int, db: AsyncSession = Depends(get_db)):
    return ModelListResponse(
        models=await ModelProviderService(db).list_available_models(provider_id)
    )
