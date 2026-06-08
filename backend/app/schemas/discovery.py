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
    targets: list[str] = Field(default_factory=list, max_length=32)
    use_default_ranges: bool = True
    infrastructure_device_ids: list[str] = Field(default_factory=list, max_length=16)
    include_arp_mac: bool = True
    max_targets: int | None = Field(default=None, ge=1, le=1024)
    rfc1918_only: bool = True
    use_credential_profiles: bool = True
    credential_profile_ids: list[str] = Field(default_factory=list, max_length=32)
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
    discovery_source: str | None = None
    fingerprint_methods: list[str] = Field(default_factory=list)
    matched_credential_profile_id: str | None = None
    matched_credential_profile_name: str | None = None


class DiscoveryScanResult(BaseModel):
    scanned: int
    candidates: list[DiscoveryCandidate]
    scan_prefixes: list[str] = Field(default_factory=list)
    l2_neighbors_found: int = 0
    infrastructure_sources: list[str] = Field(default_factory=list)


class DiscoveryPrefixesResult(BaseModel):
    prefixes: list[str]


class DiscoveryImportRequest(BaseModel):
    candidates: list[DiscoveryCandidate]
    enable_connectors: bool = False
    import_credentials: bool = False
    username: str | None = None
    password: str | None = None


class DiscoveryImportResult(BaseModel):
    imported: int
    skipped: int