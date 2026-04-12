from datetime import datetime

from pydantic import BaseModel, EmailStr


class SignUpRequest(BaseModel):
    name: str
    email: EmailStr
    password: str


class SignInRequest(BaseModel):
    email: EmailStr
    password: str


class UserResponse(BaseModel):
    id: str
    name: str
    email: str
    role: str
    banned: bool
    ban_reason: str | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class SessionResponse(BaseModel):
    user: UserResponse


class UserListResponse(BaseModel):
    items: list[UserResponse]
    total: int
    offset: int
    limit: int


class CreateUserRequest(BaseModel):
    name: str
    email: EmailStr
    password: str
    role: str = "doctor"


class UpdateUserRoleRequest(BaseModel):
    role: str


class BanUserRequest(BaseModel):
    ban_reason: str | None = None
