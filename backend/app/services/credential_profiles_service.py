from __future__ import annotations

import uuid
from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.collectors.factory import CONNECTOR_BY_TYPE
from app.models.settings import AppSettings
from app.schemas.credentials import (
    CredentialProfileRead,
    CredentialProfileWrite,
    CredentialProfilesResponse,
)
from app.services.crypto import decrypt_credentials, encrypt_credentials

SETTINGS_KEY = "credential_profiles"
DEVICE_TYPES = frozenset(CONNECTOR_BY_TYPE.keys())


@dataclass(frozen=True)
class ResolvedCredential:
    profile_id: str | None
    profile_name: str | None
    username: str
    password: str
    device_types: tuple[str, ...]


def _validate_device_types(device_types: list[str]) -> list[str]:
    invalid = [value for value in device_types if value not in DEVICE_TYPES]
    if invalid:
        raise ValueError(
            f"Unsupported device_types: {', '.join(invalid)}. "
            f"Choose from: {', '.join(sorted(DEVICE_TYPES))}"
        )
    return device_types


def _load_raw_profiles(db: Session) -> list[dict]:
    row = db.get(AppSettings, SETTINGS_KEY)
    if row is None or not row.value:
        return []
    profiles = row.value.get("profiles", [])
    return profiles if isinstance(profiles, list) else []


def _save_raw_profiles(db: Session, profiles: list[dict]) -> None:
    row = db.get(AppSettings, SETTINGS_KEY)
    payload = {"profiles": profiles}
    if row is None:
        db.add(AppSettings(key=SETTINGS_KEY, value=payload))
    else:
        row.value = payload
    db.commit()


def _to_read(profile: dict) -> CredentialProfileRead:
    return CredentialProfileRead(
        id=profile["id"],
        name=profile["name"],
        username=profile.get("username", ""),
        password_configured=bool(profile.get("credentials_encrypted")),
        device_types=list(profile.get("device_types") or []),
        enabled=bool(profile.get("enabled", True)),
    )


def get_credential_profiles(db: Session) -> CredentialProfilesResponse:
    return CredentialProfilesResponse(profiles=[_to_read(p) for p in _load_raw_profiles(db)])


def update_credential_profiles(
    db: Session, profiles: list[CredentialProfileWrite]
) -> CredentialProfilesResponse:
    existing = {p["id"]: p for p in _load_raw_profiles(db)}
    stored: list[dict] = []

    for item in profiles:
        device_types = _validate_device_types(item.device_types)
        profile_id = item.id or str(uuid.uuid4())
        previous = existing.get(profile_id, {})

        if item.password:
            encrypted = encrypt_credentials(item.username, item.password)
        else:
            encrypted = previous.get("credentials_encrypted")
            if not encrypted:
                raise ValueError(f"Password required for new profile '{item.name}'")

        stored.append(
            {
                "id": profile_id,
                "name": item.name.strip(),
                "username": item.username.strip(),
                "credentials_encrypted": encrypted,
                "device_types": device_types,
                "enabled": item.enabled,
            }
        )

    _save_raw_profiles(db, stored)
    return get_credential_profiles(db)


def resolve_profile(profile: dict) -> ResolvedCredential | None:
    if not profile.get("enabled", True):
        return None
    username, password = decrypt_credentials(profile.get("credentials_encrypted"))
    if not username or not password:
        return None
    return ResolvedCredential(
        profile_id=profile["id"],
        profile_name=profile.get("name"),
        username=username,
        password=password,
        device_types=tuple(profile.get("device_types") or []),
    )


def _matches_device_type(profile: ResolvedCredential, device_type: str | None) -> bool:
    if not profile.device_types:
        return True
    if not device_type:
        return True
    return device_type in profile.device_types


def resolve_credentials_for_discovery(
    db: Session,
    *,
    profile_ids: list[str] | None = None,
    username: str | None = None,
    password: str | None = None,
    device_type: str | None = None,
    use_profiles: bool = True,
) -> list[ResolvedCredential]:
    attempts: list[ResolvedCredential] = []

    if username and password:
        attempts.append(
            ResolvedCredential(
                profile_id=None,
                profile_name="manual",
                username=username,
                password=password,
                device_types=(),
            )
        )

    if use_profiles:
        selected_ids = set(profile_ids or [])
        use_all = not profile_ids
        for raw in _load_raw_profiles(db):
            if use_all or raw.get("id") in selected_ids:
                resolved = resolve_profile(raw)
                if resolved and _matches_device_type(resolved, device_type):
                    attempts.append(resolved)

    return attempts


def get_resolved_profile_by_id(db: Session, profile_id: str) -> ResolvedCredential | None:
    for raw in _load_raw_profiles(db):
        if raw.get("id") == profile_id:
            return resolve_profile(raw)
    return None