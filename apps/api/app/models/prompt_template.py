import uuid
from datetime import datetime

from pydantic import BaseModel


class PromptTemplateResponse(BaseModel):
    id: uuid.UUID
    slug: str
    version: int
    is_active: bool
    title: str
    description: str
    content: str
    variables: str
    created_by: str | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class PromptTemplateListResponse(BaseModel):
    items: list[PromptTemplateResponse]
    total: int
    offset: int
    limit: int


class PromptTemplateUpdate(BaseModel):
    content: str
    title: str | None = None
    description: str | None = None
    variables: str | None = None


class PromptVersionListResponse(BaseModel):
    slug: str
    versions: list[PromptTemplateResponse]
