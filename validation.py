"""Validation of incoming health check payloads."""

from datetime import date

GENERAL_STATUSES = ("OK", "PROBLEM", "IKKJE_VURDERT")
SECURITY_STATUSES = ("TRYGG", "PATCHA", "SÅRBAR", "KOMPROMITTERT")
PRODUCTS = ("SeedSigner", "Blockstream Jade", "Nunchuk", "Sparrow Wallet")
MAX_VERSION_LENGTH = 100
MAX_PATH_LENGTH = 200
MAX_NOTES_LENGTH = 2000
MAX_COMMENTS_LENGTH = 4000


class ValidationError(ValueError):
    """Raised when a payload does not match the expected health check shape."""


def validate_health_check(payload, key_ids):
    """Return a normalized health check ready for storage."""
    if not isinstance(payload, dict):
        raise ValidationError("payload must be a JSON object")

    return {
        "checked_at": _date(payload.get("checked_at"), "checked_at"),
        "next_check_due": _date(payload.get("next_check_due"), "next_check_due"),
        "software_compatibility_status": _status(
            payload.get("software_compatibility_status"),
            "software_compatibility_status",
            GENERAL_STATUSES,
        ),
        "sparrow_version": _text(payload.get("sparrow_version"), "sparrow_version", MAX_VERSION_LENGTH),
        "nunchuk_version": _text(payload.get("nunchuk_version"), "nunchuk_version", MAX_VERSION_LENGTH),
        "software_comments": _text(payload.get("software_comments"), "software_comments", MAX_NOTES_LENGTH),
        "contact_info_verified": _flag(payload.get("contact_info_verified"), "contact_info_verified"),
        "comments": _text(payload.get("comments"), "comments", MAX_COMMENTS_LENGTH),
        "key_checks": _key_checks(payload.get("key_checks"), key_ids),
        "tool_checks": _tool_checks(payload.get("tool_checks")),
        "ai_security_checks": _ai_security_checks(payload.get("ai_security_checks")),
    }


def _date(value, field):
    if not isinstance(value, str):
        raise ValidationError(f"{field} must be an ISO date")
    try:
        parsed = date.fromisoformat(value)
    except ValueError as error:
        raise ValidationError(f"{field} must be an ISO date") from error
    return parsed.isoformat()


def _optional_date(value, field):
    if value is None or value == "":
        return None
    return _date(value, field)


def _status(value, field, allowed):
    if value not in allowed:
        raise ValidationError(f"{field} is not an allowed status")
    return value


def _optional_status(value, field):
    if value is None or value == "":
        return None
    return _status(value, field, GENERAL_STATUSES)


def _flag(value, field):
    if value is None or value == "":
        return None
    if isinstance(value, bool):
        return int(value)
    if value in (0, 1):
        return int(value)
    raise ValidationError(f"{field} must be 0 or 1")


def _text(value, field, max_length):
    if value is None:
        text = ""
    elif isinstance(value, str):
        text = value.strip()
    else:
        raise ValidationError(f"{field} must be text")
    if len(text) > max_length:
        raise ValidationError(f"{field} is too long")
    return text or None


def _key_checks(entries, key_ids):
    if not isinstance(entries, list):
        raise ValidationError("key_checks must be a list")
    expected = set(key_ids)
    seen = set()
    normalized = []
    for entry in entries:
        if not isinstance(entry, dict):
            raise ValidationError("each key check must be an object")
        key_id = entry.get("key_id")
        if not isinstance(key_id, int) or key_id not in expected:
            raise ValidationError("key_id is not a configured key")
        if key_id in seen:
            raise ValidationError("each key may only be checked once")
        seen.add(key_id)
        normalized.append({
            "key_id": key_id,
            "available": _flag(entry.get("available"), "available"),
            "hardware_works": _flag(entry.get("hardware_works"), "hardware_works"),
            "firmware_version": _text(entry.get("firmware_version"), "firmware_version", MAX_VERSION_LENGTH),
            "seed_backup_status": _optional_status(entry.get("seed_backup_status"), "seed_backup_status"),
            "seed_backup_verified": _flag(entry.get("seed_backup_verified"), "seed_backup_verified"),
            "cloud_health_status": _optional_status(entry.get("cloud_health_status"), "cloud_health_status"),
            "cloud_provider_operational": _flag(entry.get("cloud_provider_operational"), "cloud_provider_operational"),
            "address_verified": _flag(entry.get("address_verified"), "address_verified"),
            "derivation_height": _text(entry.get("derivation_height"), "derivation_height", MAX_PATH_LENGTH),
            "address_path_verified": _flag(entry.get("address_path_verified"), "address_path_verified"),
            "address_path": _text(entry.get("address_path"), "address_path", MAX_PATH_LENGTH),
            "comments": _text(entry.get("comments"), "comments", MAX_NOTES_LENGTH),
        })
    if seen != expected:
        raise ValidationError("every configured key must be checked")
    return normalized


def _tool_checks(entries):
    if not isinstance(entries, list):
        raise ValidationError("tool_checks must be a list")
    seen = set()
    normalized = []
    for entry in entries:
        if not isinstance(entry, dict):
            raise ValidationError("each tool check must be an object")
        product = entry.get("product")
        if product not in PRODUCTS:
            raise ValidationError("tool check product is not supported")
        if product in seen:
            raise ValidationError("each product may only be checked once")
        seen.add(product)
        normalized.append({
            "product": product,
            "bip327_status": _status(entry.get("bip327_status"), "bip327_status", GENERAL_STATUSES),
            "slip39_status": _status(entry.get("slip39_status"), "slip39_status", GENERAL_STATUSES),
            "version": _text(entry.get("version"), "version", MAX_VERSION_LENGTH),
            "checked_at": _optional_date(entry.get("checked_at"), "checked_at"),
            "notes": _text(entry.get("notes"), "notes", MAX_NOTES_LENGTH),
        })
    if seen != set(PRODUCTS):
        raise ValidationError("every supported product must be checked")
    return normalized


def _ai_security_checks(entries):
    if not isinstance(entries, list):
        raise ValidationError("ai_security_checks must be a list")
    seen = set()
    normalized = []
    for entry in entries:
        if not isinstance(entry, dict):
            raise ValidationError("each security check must be an object")
        provider = entry.get("provider")
        if provider not in PRODUCTS:
            raise ValidationError("security check provider is not supported")
        if provider in seen:
            raise ValidationError("each provider may only be checked once")
        seen.add(provider)
        normalized.append({
            "provider": provider,
            "status": _status(entry.get("status"), "status", SECURITY_STATUSES),
            "comments": _text(entry.get("comments"), "comments", MAX_NOTES_LENGTH),
        })
    if seen != set(PRODUCTS):
        raise ValidationError("every provider must have a security status")
    return normalized
