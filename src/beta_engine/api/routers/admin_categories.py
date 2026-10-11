from __future__ import annotations

from fastapi import APIRouter, Depends

from beta_engine.api.deps import get_category_service
from beta_engine.application.category_service import CategoriesResponse, CategoryService

router = APIRouter(prefix="/admin/categories", tags=["admin-categories"])


@router.get("", response_model=CategoriesResponse)
def get_categories(service: CategoryService = Depends(get_category_service)) -> CategoriesResponse:
    return service.list_categories()
