from pydantic import BaseModel, Field


class CredentialTestRequest(BaseModel):
    username: str | None = None
    password: str | None = None


class CredentialTestResult(BaseModel):
    ok: bool
    message: str
    device_type: str
    overall: str | None = None


class DiscoveryScanRequest(BaseModel):
    targets: list[str] = Field(min_length=1, max_length=32)
    username: str | None = None
    password: str | None = None
    device_type_hint: str | None = None


class DiscoveryCandidate(BaseModel):
    target: str
    reachable: bool
    detected_type: str | None = None
    suggested_name: str | None = None
    suggested_hostname: str | None = None
    credentials_ok: bool | None = None
    message: str = ""


class DiscoveryScanResult(BaseModel):
    scanned: int
    candidates: list[DiscoveryCandidate]


class DiscoveryImportRequest(BaseModel):
    candidates: list[DiscoveryCandidate]
    enable_connectors: bool = False
    import_credentials: bool = False
    username: str | None = None
    password: str | None = None


class DiscoveryImportResult(BaseModel):
    imported: int
    skipped: int