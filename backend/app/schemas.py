from pydantic import BaseModel, EmailStr, Field, field_validator
from typing import Literal

class RegisterInput(BaseModel):
    full_name: str = Field(min_length=2, max_length=160)
    email: EmailStr
    password: str = Field(min_length=10, max_length=128)
    confirm_password: str
    @field_validator('password')
    @classmethod
    def strong_password(cls, value: str):
        if not any(c.isupper() for c in value) or not any(c.islower() for c in value) or not any(c.isdigit() for c in value):
            raise ValueError('Password must include upper-case, lower-case, and numeric characters.')
        return value

class LoginInput(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=128)

class ForgotPasswordInput(BaseModel):
    email: EmailStr

class ResetPasswordInput(BaseModel):
    token: str = Field(min_length=20)
    password: str = Field(min_length=10, max_length=128)
    confirm_password: str

class VerificationInput(BaseModel):
    input_type: Literal['text', 'url', 'claim']
    content: str = Field(min_length=3, max_length=24000)

class ShareInput(BaseModel):
    is_public: bool
