"""Validation of incoming health check payloads.

One submission records one selected key only, as decided in section 19 of the
requirements. The next check date is derived on the server and never taken from
the client.
"""

from datetime import date

GENERAL_STATUSES = ("OK", "PROBLEM", "IKKJE_VURDERT")
VERIFICATION_STATUSES = ("OK", "PROBLEM")
SECURITY_STATUSES = ("SECURE", "PATCHED", "VULNERABLE", "COMPROMISED")
WALLET_SOFTWARE = ("Sparrow Wallet", "Nunchuk")
KEY_PRODUCTS = {1: "SeedSigner", 2: "Blockstream Jade", 3: "Nunchuk"}
CLOUD_KEY_NUMBER = 3
MAX_VERSION_LENGTH = 100
MAX_PATH_LENGTH = 200
MAX_NOTES_LENGTH = 2000
MAX_COMMENTS_LENGTH = 4000


class ValidationError(ValueError):
    """Raised when a payload does not match the expected health check shape."""


def next_check_due(checked_at):
    """Return the check date one calendar year later, clamping 29 February."""
    checked = date.fromisoformat(checked_at)
    try:
        return checked.replace(year=checked.year + 1).isoformat()
    except ValueError:
        return checked.replace(year=checked.year + 1, day=28).isoformat()


def validate_health_check(payload, keys):
    """Return a normalized single-key health check ready for storage."""
    if not isinstance(payload, dict):
        raise ValidationError("payload must be a JSON object")

    entry = payload.get("key_check")
    if not isinstance(entry, dict):
        raise ValidationError("key_check must be an object")

    key = _select_key(entry.get("key_id"), keys)
    checked_at = _date(payload.get("checked_at"), "checked_at")
    wallet_software = _wallet_software(payload.get("wallet_software"), key)

    return {
        "checked_at": checked_at,
        "next_check_due": next_check_due(checked_at),
        "wallet_software": wallet_software,
        "software_version": _text(
            payload.get("software_version"), "software_version", MAX_VERSION_LENGTH
        ),
        "software_compatibility_status": _status(
            payload.get("software_compatibility_status"),
            "software_compatibility_status",
            GENERAL_STATUSES,
        ),
        "software_comments": _text(
            payload.get("software_comments"), "software_comments", MAX_NOTES_LENGTH
        ),
        "contact_info_verified": _flag(
            payload.get("contact_info_verified"), "contact_info_verified"
        ),
        "comments": _text(payload.get("comments"), "comments", MAX_COMMENTS_LENGTH),
        "key_check": _key_check(entry, key),
        "tool_checks": _tool_checks(
            payload.get("tool_checks"), _expected_products(key, wallet_software)
        ),
        "ai_security_checks": _ai_security_checks(
            payload.get("ai_security_checks"), _expected_providers(key)
        ),
    }


def _select_key(key_id, keys):
    """Return the configured key profile with the given id."""
    if isinstance(key_id, bool) or not isinstance(key_id, int):
        raise ValidationError("key_id must be a configured key")
    for key in keys:
        if key["id"] == key_id:
            return key
    raise ValidationError("key_id is not a configured key")


def _wallet_software(value, key):
    """Return the selected wallet software, fixed to Nunchuk for the cloud key."""
    if value not in WALLET_SOFTWARE:
        raise ValidationError("wallet_software must be Sparrow Wallet or Nunchuk")
    if key["key_number"] == CLOUD_KEY_NUMBER and value != "Nunchuk":
        raise ValidationError("Nunchuk is the only wallet software for the cloud key")
    return value


def _expected_products(key, wallet_software):
    """Return the products to record BIP327/SLIP39 for, without duplicates."""
    return tuple(dict.fromkeys((KEY_PRODUCTS[key["key_number"]], wallet_software)))


def _expected_providers(key):
    """Return the security status providers relevant to the selected key."""
    if key["key_number"] == CLOUD_KEY_NUMBER:
        return ("Nunchuk",)
    return (KEY_PRODUCTS[key["key_number"]], "Sparrow Wallet", "Nunchuk")


def _key_check(entry, key):
    """Return the normalized check for the selected key."""
    available = _flag(entry.get("available"), "available")
    check = {
        "key_id": key["id"],
        "available": available,
        "hardware_works": None,
        "firmware_version": None,
        "seed_backup_verified": None,
        "cloud_health_status": None,
        "cloud_provider_operational": None,
        "address_path_verified": None,
        "address_path": None,
        "comments": _text(entry.get("comments"), "comments", MAX_NOTES_LENGTH),
    }
    if available == 0:
        # The remaining checks could not be performed, so nothing is recorded.
        # The cloud key keeps its derived cloud results, because those describe
        # the provider rather than a check that could not be run (section 20).
        if key["type"] == "cloud":
            check["cloud_health_status"] = _optional_status(
                entry.get("cloud_health_status"), "cloud_health_status"
            )
            check["cloud_provider_operational"] = _flag(
                entry.get("cloud_provider_operational"), "cloud_provider_operational"
            )
        return check

    required = available == 1
    if key["type"] == "hardware":
        check["hardware_works"] = _flag(entry.get("hardware_works"), "hardware_works")
        check["firmware_version"] = _text(
            entry.get("firmware_version"), "firmware_version", MAX_VERSION_LENGTH
        )
        check["seed_backup_verified"] = _verification(
            entry.get("seed_backup_verified"), "seed_backup_verified", required
        )
    else:
        check["cloud_health_status"] = _optional_status(
            entry.get("cloud_health_status"), "cloud_health_status"
        )
        check["cloud_provider_operational"] = _flag(
            entry.get("cloud_provider_operational"), "cloud_provider_operational"
        )
    check["address_path_verified"] = _verification(
        entry.get("address_path_verified"), "address_path_verified", required
    )
    check["address_path"] = _text(entry.get("address_path"), "address_path", MAX_PATH_LENGTH)
    return check


def _date(value, field):
    if not isinstance(value, str):
        raise ValidationError(f"{field} must be an ISO date")
    try:
        parsed = date.fromisoformat(value)
    except ValueError as error:
        raise ValidationError(f"{field} must be an ISO date") from error
    return parsed.isoformat()


def _status(value, field, allowed):
    if value not in allowed:
        raise ValidationError(f"{field} is not an allowed status")
    return value


def _optional_status(value, field):
    if value is None or value == "":
        return None
    return _status(value, field, GENERAL_STATUSES)


def _verification(value, field, required):
    """Return OK/PROBLEM, requiring a value when the key was available."""
    if value is None or value == "":
        if required:
            raise ValidationError(f"{field} is required when the key is available")
        return None
    return _status(value, field, VERIFICATION_STATUSES)


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


def _tool_checks(entries, expected):
    """Return the BIP327/SLIP39 rows for the key product and selected software."""
    if not isinstance(entries, list):
        raise ValidationError("tool_checks must be a list")
    allowed = set(expected)
    seen = set()
    normalized = []
    for entry in entries:
        if not isinstance(entry, dict):
            raise ValidationError("each tool check must be an object")
        product = entry.get("product")
        if product not in allowed:
            raise ValidationError("tool check product is not relevant for this submission")
        if product in seen:
            raise ValidationError("each product may only be checked once")
        seen.add(product)
        normalized.append({
            "product": product,
            "bip327_status": _status(entry.get("bip327_status"), "bip327_status", GENERAL_STATUSES),
            "slip39_status": _status(entry.get("slip39_status"), "slip39_status", GENERAL_STATUSES),
        })
    if seen != allowed:
        raise ValidationError("every relevant product must be checked")
    return normalized


def _ai_security_checks(entries, expected):
    """Return the security status rows relevant to the selected key."""
    if not isinstance(entries, list):
        raise ValidationError("ai_security_checks must be a list")
    allowed = set(expected)
    seen = set()
    normalized = []
    for entry in entries:
        if not isinstance(entry, dict):
            raise ValidationError("each security check must be an object")
        provider = entry.get("provider")
        if provider not in allowed:
            raise ValidationError("security check provider is not relevant for this submission")
        if provider in seen:
            raise ValidationError("each provider may only be checked once")
        seen.add(provider)
        normalized.append({
            "provider": provider,
            "status": _status(entry.get("status"), "status", SECURITY_STATUSES),
            "comments": _text(entry.get("comments"), "comments", MAX_NOTES_LENGTH),
        })
    if seen != allowed:
        raise ValidationError("every relevant provider must have a security status")
    return normalized
