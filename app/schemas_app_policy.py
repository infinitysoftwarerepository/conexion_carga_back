from __future__ import annotations

from pydantic import BaseModel


class AppVersionPolicyOut(BaseModel):
    platform: str
    current_version: str | None = None
    current_build: int | None = None
    force_update: bool
    comparison_mode: str
    min_supported_version: str | None = None
    min_supported_build: int | None = None
    latest_version: str | None = None
    latest_build: int | None = None
    store_url: str | None = None
    message: str | None = None


class AppVersionPolicyIn(BaseModel):
    platform: str
    version: str | None = None
    build: int | None = None
