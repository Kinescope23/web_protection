from pydantic import BaseModel, EmailStr, Field
from typing import Optional, List
from datetime import datetime


class UserRegister(BaseModel):
    email: EmailStr
    username: str = Field(min_length=3, max_length=64)
    password: str = Field(min_length=8)
    invitation_key: str


class UserLogin(BaseModel):
    email: EmailStr
    password: str
    totp_code: Optional[str] = None


class UserResponse(BaseModel):
    id: int
    email: str
    username: str
    role: str
    is_2fa_enabled: bool
    avatar_url: Optional[str] = None


class TokenResponse(BaseModel):
    access_token: str
    token_type: str


class ChangePassword(BaseModel):
    current_password: str
    new_password: str = Field(min_length=8)


class APITokenCreate(BaseModel):
    name: str = Field(min_length=1, max_length=128)
    scopes: Optional[List[str]] = None
