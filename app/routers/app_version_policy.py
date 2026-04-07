from __future__ import annotations

import os
import re
from typing import Optional

from fastapi import APIRouter, Query

from app.schemas_app_policy import AppVersionPolicyOut

router = APIRouter(prefix="/api/app", tags=["App Version Policy"])


def _parse_int(value: Optional[str]) -> Optional[int]:
    if value is None:
        return None
    try:
        return int(str(value).strip())
    except ValueError:
        return None


def _parse_version(value: Optional[str]) -> list[int]:
    if not value:
        return []

    tokens = re.split(r"[.\-+_]", str(value).strip())
    numbers: list[int] = []
    for token in tokens:
        if not token:
            continue
        match = re.match(r"(\d+)", token)
        if match:
            numbers.append(int(match.group(1)))
    return numbers


def _compare_versions(a: Optional[str], b: Optional[str]) -> int:
    a_parts = _parse_version(a)
    b_parts = _parse_version(b)

    if not a_parts and not b_parts:
        return 0

    length = max(len(a_parts), len(b_parts))
    a_parts += [0] * (length - len(a_parts))
    b_parts += [0] * (length - len(b_parts))

    if a_parts == b_parts:
        return 0
    return -1 if a_parts < b_parts else 1


def _env_for_platform(platform: str, suffix: str, default: str = "") -> str:
    key = f"APP_{suffix}_{platform.upper()}"
    return os.getenv(key, default)


@router.get("/version-policy", response_model=AppVersionPolicyOut)
def get_version_policy(
    platform: str = Query(..., description="android | ios"),
    version: Optional[str] = Query(default=None),
    build: Optional[int] = Query(default=None),
):
    plat = (platform or "").strip().lower()
    if plat not in {"android", "ios"}:
        plat = "android"

    min_version = _env_for_platform(plat, "MIN_VERSION", "")
    min_build = _parse_int(_env_for_platform(plat, "MIN_BUILD", ""))
    latest_version = _env_for_platform(plat, "LATEST_VERSION", "") or None
    latest_build = _parse_int(_env_for_platform(plat, "LATEST_BUILD", ""))
    store_url = _env_for_platform(plat, "STORE_URL", "") or None
    message = _env_for_platform(
        plat,
        "FORCE_UPDATE_MESSAGE",
        "Debes actualizar la app para continuar.",
    )
    if not store_url and plat == "android":
        store_url = (
            "https://play.google.com/store/apps/details"
            "?id=com.infinitysoftware.conexioncarga"
        )

    force_update = False
    comparison_mode = "version"

    # Android puede permanecer con version visible 1.0.0 por varias entregas.
    # Por eso, cuando existe min_build, el control principal debe ser el build.
    if min_build is not None:
        comparison_mode = "build"
        if build is not None and build < min_build:
            force_update = True
    elif min_version:
        comparison_mode = "version"
        if _compare_versions(version, min_version) < 0:
            force_update = True

    # Si no llegó build pero sí existe versión mínima, usamos la visible como respaldo.
    if min_build is not None and build is None and min_version:
        comparison_mode = "build_with_version_fallback"
        if _compare_versions(version, min_version) < 0:
            force_update = True

    return AppVersionPolicyOut(
        platform=plat,
        current_version=version,
        current_build=build,
        force_update=force_update,
        comparison_mode=comparison_mode,
        min_supported_version=min_version or None,
        min_supported_build=min_build,
        latest_version=latest_version,
        latest_build=latest_build,
        store_url=store_url,
        message=message,
    )
