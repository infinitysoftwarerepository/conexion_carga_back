from __future__ import annotations

import re


PHONE_INTL_REGEX = re.compile(r'^\+\d{7,18}$')
PHONE_CODE_DIGITS_REGEX = re.compile(r'^\d{1,5}$')
PHONE_NUMBER_DIGITS_REGEX = re.compile(r'^\d{4,15}$')


def normalize_text(value: object, max_length: int | None = None) -> str | None:
    if value is None:
        return None

    text = str(value).strip()
    if not text:
        return None

    if max_length is not None:
        text = text[:max_length].strip()

    return text or None


def normalize_document(value: object, max_length: int = 80) -> str | None:
    text = normalize_text(value, max_length=max_length)
    if not text:
        return None

    return re.sub(r'\s+', '', text)


def normalize_phone_code(value: object) -> str | None:
    text = normalize_text(value, max_length=10)
    if not text:
        return None

    digits = re.sub(r'\D+', '', text)
    if not digits or not PHONE_CODE_DIGITS_REGEX.fullmatch(digits):
        raise ValueError('El código de país no es válido.')

    return f'+{digits}'


def normalize_phone_number(value: object) -> str | None:
    text = normalize_text(value, max_length=20)
    if not text:
        return None

    digits = re.sub(r'\D+', '', text)
    if not digits or not PHONE_NUMBER_DIGITS_REGEX.fullmatch(digits):
        raise ValueError(
            'El número de WhatsApp solo debe contener números válidos.',
        )

    return digits


def normalize_international_phone(value: object) -> str | None:
    text = normalize_text(value, max_length=20)
    if not text:
        return None

    digits = re.sub(r'\D+', '', text)
    normalized = f'+{digits}' if digits else None

    if not normalized or not PHONE_INTL_REGEX.fullmatch(normalized):
        raise ValueError(
            'El número de WhatsApp debe estar en formato internacional, por ejemplo +573136485468.',
        )

    return normalized


def compose_phone(phone_code: object, phone_number: object) -> str | None:
    code = normalize_phone_code(phone_code)
    number = normalize_phone_number(phone_number)

    if not code and not number:
        return None

    if not code or not number:
        raise ValueError(
            'Debes seleccionar el código de país y escribir el número de WhatsApp.',
        )

    return normalize_international_phone(f'{code}{number}')


def resolve_document_and_phone(
    *,
    document: object = None,
    phone: object = None,
    phone_code: object = None,
    phone_number: object = None,
    require_document: bool = False,
    require_phone: bool = False,
    allow_legacy_document_from_phone: bool = False,
) -> tuple[str | None, str | None]:
    resolved_document = normalize_document(document)
    resolved_phone: str | None = None

    has_phone_parts = normalize_text(phone_code) is not None or normalize_text(phone_number) is not None
    raw_phone = normalize_text(phone)

    if has_phone_parts:
        resolved_phone = compose_phone(phone_code, phone_number)
    elif raw_phone:
        if (
            allow_legacy_document_from_phone
            and not resolved_document
            and not str(raw_phone).strip().startswith('+')
        ):
            resolved_document = normalize_document(raw_phone)
            resolved_phone = None
        else:
            try:
                resolved_phone = normalize_international_phone(raw_phone)
            except ValueError:
                if allow_legacy_document_from_phone and not resolved_document:
                    resolved_document = normalize_document(raw_phone)
                    resolved_phone = None
                else:
                    raise

    if require_document and not resolved_document:
        raise ValueError('La identificación es obligatoria.')

    if require_phone and not resolved_phone:
        raise ValueError(
            'El número de WhatsApp es obligatorio y debe estar en formato internacional.',
        )

    return resolved_document, resolved_phone


def split_stored_document_and_phone(
    document: object = None,
    phone: object = None,
) -> tuple[str | None, str | None]:
    resolved_document = normalize_document(document)
    raw_phone = normalize_text(phone, max_length=30)

    if not raw_phone:
        return resolved_document, None

    if not str(raw_phone).strip().startswith('+'):
        if not resolved_document:
            resolved_document = normalize_document(raw_phone)
        return resolved_document, None

    try:
        resolved_phone = normalize_international_phone(raw_phone)
    except ValueError:
        if not resolved_document:
            resolved_document = normalize_document(raw_phone)
        return resolved_document, None

    return resolved_document, resolved_phone
