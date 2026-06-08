from pydantic import BaseModel, Field


class CredentialProfileRead(BaseModel):
    id: str
    name: str
    username: str
    password_configured: bool
    device_types: list[str] = Field(default_factory=list)
    enabled: bool = True


class CredentialProfileWrite(BaseModel):
    id: str | None = None
    name: str = Field(min_length=1, max_length=128)
    username: str = Field(min_length=1, max_length=128)
    password: str | None = None
    device_types: list[str] = Field(default_factory=list, max_length=8)
    enabled: bool = True


class CredentialProfilesResponse(BaseModel):
    profiles: list[CredentialProfileRead] = Field(default_factory=list)