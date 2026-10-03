"""Validation of incoming payloads.

One submission records one selected key only, as decided in section 19 of the
requirements. The next check date is derived on the server and never taken from
the client.

The stored status values are English (sections 19 and 21). General results use
``OK``, ``PROBLEM``, and ``NOT_ASSESSED``; the BIP327 and SLIP39 results use
``YES``, ``NO``, and ``NOT_ASSESSED``. The software compatibility result is an
explicit ``OK`` or ``PROBLEM`` for a hardware key (section 23.1), and the contact
confirmation is ``Confirmed current`` or ``Needs external update``.

The key setup is configured once and stored in the database (section 23.2). The
configured name is the product label of a key, and the key's type decides which
checks apply, never the key number (section 23.3).

``available`` is always recorded (section 22). When the key was not available,
the wallet software, the standards, and the security statuses are not recorded
either, so they may be left out of the payload.
"""

from datetime import date

from database import KEY_COUNT

GENERAL_STATUSES = ("OK", "PROBLEM", "NOT_ASSESSED")
# Software compatibility requires an active choice, so "not assessed" is not
# submittable for a new registration (section 23.1).
COMPATIBILITY_STATUSES = ("OK", "PROBLEM")
VERIFICATION_STATUSES = ("OK", "PROBLEM")
STANDARDS_STATUSES = ("YES", "NO", "NOT_ASSESSED")
SECURITY_STATUSES = ("SECURE", "PATCHED", "VULNERABLE", "COMPROMISED")
CONTACT_STATUSES = ("Confirmed current", "Needs external update")
KEY_TYPES = ("hardware", "cloud")
# The wallet software that is always available, whatever the key setup is
# (section 23.3).
SPARROW_SOFTWARE = "Sparrow Wallet"
MAX_KEY_NAME_LENGTH = 60
MAX_VERSION_LENGTH = 100
MAX_PATH_LENGTH = 200
MAX_NOTES_LENGTH = 2000
MAX_COMMENTS_LENGTH = 4000


class ValidationError(ValueError):
    """Raised when a payload does not match the expected shape."""


def next_check_due(checked_at):
    """Return the check date one calendar year later, clamping 29 February."""
    checked = date.fromisoformat(checked_at)
    try:
        return checked.replace(year=checked.year + 1).isoformat()
    except ValueError:
        return checked.replace(year=checked.year + 1, day=28).isoformat()


def validate_key_setup(payload):
    """Return the normalized key setup for the three key slots.

    The user names each key and picks its type once, and both are locked after
    the setup is saved (section 23.2). The names must be non-empty and unique,
    compared without regard to case.
    """
    if not isinstance(payload, dict):
        raise ValidationError("payload must be a JSON object")

    entries = payload.get("keys")
    if not isinstance(entries, list):
        raise ValidationError("keys must be a list")
    if len(entries) != KEY_COUNT:
        raise ValidationError(f"exactly {KEY_COUNT} keys must be configured")

    normalized = []
    numbers = set()
    names = set()
    for entry in entries:
        if not isinstance(entry, dict):
            raise ValidationError("each key must be an object")
        number = entry.get("key_number")
        if isinstance(number, bool) or number not in range(1, KEY_COUNT + 1):
            raise ValidationError(f"key_number must be between 1 and {KEY_COUNT}")
        if number in numbers:
            raise ValidationError("each key number may only be configured once")
        numbers.add(number)

        name = _key_name(entry.get("name"))
        if name.casefold() in names:
            raise ValidationError("key names must be unique")
        names.add(name.casefold())

        key_type = entry.get("type")
        if key_type not in KEY_TYPES:
            raise ValidationError("key type must be hardware or cloud")
        normalized.append({"key_number": number, "name": name, "type": key_type})

    return sorted(normalized, key=lambda entry: entry["key_number"])


def validate_health_check(payload, keys):
    """Return a normalized single-key health check ready for storage."""
    if not isinstance(payload, dict):
        raise ValidationError("payload must be a JSON object")

    entry = payload.get("key_check")
    if not isinstance(entry, dict):
        raise ValidationError("key_check must be an object")

    key = _select_key(entry.get("key_id"), keys)
    checked_at = _date(payload.get("checked_at"), "checked_at")
    available = _availability(entry.get("available"))
    # A key that was not available cannot be checked any further, so the wallet
    # software, the standards, and the security statuses stay empty (section 22).
    unavailable = available == 0
    wallet_software = _wallet_software(
        payload.get("wallet_software"), key, keys, unavailable
    )

    return {
        "checked_at": checked_at,
        "next_check_due": next_check_due(checked_at),
        "wallet_software": wallet_software,
        "software_version": _text(
            payload.get("software_version"), "software_version", MAX_VERSION_LENGTH
        ),
        "software_compatibility_status": _compatibility_status(
            payload.get("software_compatibility_status"), key, unavailable
        ),
        "software_comments": _text(
            payload.get("software_comments"), "software_comments", MAX_NOTES_LENGTH
        ),
        "contact_info_verified": _contact_status(payload.get("contact_info_verified")),
        "comments": _text(payload.get("comments"), "comments", MAX_COMMENTS_LENGTH),
        "key_check": _key_check(entry, key, available),
        "tool_checks": _tool_checks(
            payload.get("tool_checks"), key, wallet_software, unavailable
        ),
        "ai_security_checks": _ai_security_checks(
            payload.get("ai_security_checks"), key, wallet_software, unavailable
        ),
    }


def _key_name(value):
    """Return the configured key name, which must be non-empty text."""
    if not isinstance(value, str):
        raise ValidationError("key name must be text")
    name = value.strip()
    if not name:
        raise ValidationError("key name must not be empty")
    if len(name) > MAX_KEY_NAME_LENGTH:
        raise ValidationError("key name is too long")
    return name


def _select_key(key_id, keys):
    """Return the configured key profile with the given id."""
    if isinstance(key_id, bool) or not isinstance(key_id, int):
        raise ValidationError("key_id must be a configured key")
    for key in keys:
        if key["id"] == key_id:
            return key
    raise ValidationError("key_id is not a configured key")


def _availability(value):
    """Return 0 or 1. Availability is always recorded (section 22)."""
    available = _flag(value, "available")
    if available is None:
        raise ValidationError("available is required")
    return available


def _wallet_software_choices(keys):
    """Return the wallet software choices.

    Sparrow is always available, and every configured cloud key contributes its
    own name. A hardware key name is never a software choice (section 23.3).
    """
    names = (key["name"] for key in keys if key["type"] == "cloud")
    return tuple(dict.fromkeys((SPARROW_SOFTWARE, *names)))


def _wallet_software(value, key, keys, unavailable):
    """Return the selected wallet software.

    A cloud key records its own name, because the provider is the software for
    that key (section 23.3). A key that was not available records no software,
    so the field must be left out then (section 22).
    """
    if value is None or value == "":
        if unavailable:
            return None
        raise ValidationError("wallet_software is required when the key is available")
    if unavailable:
        raise ValidationError(
            "wallet_software cannot be recorded when the key was not available"
        )
    if key["type"] == "cloud":
        if value != key["name"]:
            raise ValidationError("a cloud key records its own name as the wallet software")
        return value
    if value not in _wallet_software_choices(keys):
        raise ValidationError(
            f"wallet_software must be {SPARROW_SOFTWARE} or the name of a cloud key"
        )
    return value


def _compatibility_status(value, key, unavailable):
    """Return the software compatibility result.

    The cloud key derives it from availability (section 20), so only the derived
    value is accepted there. A hardware key requires an active ``OK`` or
    ``PROBLEM``, and a missing value is a ``400`` (section 23.1).
    """
    if key["type"] == "cloud":
        derived = "NOT_ASSESSED" if unavailable else "OK"
        if value not in (None, "", derived):
            raise ValidationError(
                "software_compatibility_status is derived for the cloud key"
            )
        return derived
    if unavailable:
        # The remaining checks could not be performed, so the result stays not
        # assessed and no other value may accompany it (section 22).
        if value not in (None, "", "NOT_ASSESSED"):
            raise ValidationError(
                "software_compatibility_status cannot be recorded "
                "when the key was not available"
            )
        return "NOT_ASSESSED"
    return _status(value, "software_compatibility_status", COMPATIBILITY_STATUSES)


def _contact_status(value):
    """Return the contact confirmation for the selected key's holder.

    Only the status is recorded, never names, addresses, phone numbers, or
    credentials (section 23.1). A confirmation that was not assessed stays empty.
    """
    if value is None or value == "":
        return None
    return _status(value, "contact_info_verified", CONTACT_STATUSES)


def _require_nothing_recorded(entries, field):
    """Reject results for a key that was not available (section 22)."""
    if entries is None or entries == []:
        return
    raise ValidationError(f"{field} cannot be recorded when the key was not available")


def _expected_labels(key, wallet_software):
    """Return the labels a submission records, without duplicates.

    Both the standards and the security statuses are recorded for the selected
    key, by its configured name, and for the selected wallet software
    (section 23.3). A cloud key that is named after its own software therefore
    contributes one label only.
    """
    return tuple(dict.fromkeys((key["name"], wallet_software)))


def _key_check(entry, key, available):
    """Return the normalized check for the selected key."""
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


def _tool_checks(entries, key, wallet_software, unavailable):
    """Return the BIP327/SLIP39 rows for the selected key and wallet software."""
    if unavailable:
        _require_nothing_recorded(entries, "tool_checks")
        return []
    if not isinstance(entries, list):
        raise ValidationError("tool_checks must be a list")
    allowed = set(_expected_labels(key, wallet_software))
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
            "bip327_status": _status(
                entry.get("bip327_status"), "bip327_status", STANDARDS_STATUSES
            ),
            "slip39_status": _status(
                entry.get("slip39_status"), "slip39_status", STANDARDS_STATUSES
            ),
        })
    if seen != allowed:
        raise ValidationError("every relevant product must be checked")
    return normalized


def _ai_security_checks(entries, key, wallet_software, unavailable):
    """Return the security status rows for the selected key and wallet software."""
    if unavailable:
        _require_nothing_recorded(entries, "ai_security_checks")
        return []
    if not isinstance(entries, list):
        raise ValidationError("ai_security_checks must be a list")
    allowed = set(_expected_labels(key, wallet_software))
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
