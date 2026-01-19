from pydantic import BaseModel, EmailStr


class Token(BaseModel):
    """Token response schema."""
    access_token: str
    token_type: str = "bearer"


class TokenData(BaseModel):
    """Token payload data."""
    user_id: str
    email: str
    role: str


class LoginRequest(BaseModel):
    """Login request schema."""
    email: EmailStr
    password: str
