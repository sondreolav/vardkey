"""Validation of incoming payloads.

One submission records one selected key only, as decided in section 19 of the
requirements. The next check date is derived on the server and never taken from
the client.

The stored status values are English (sections 19 and 21). ``NOT_ASSESSED``
survives only as the derived ``software_compatibility_status`` of a key that
could not be checked; no other field offers or accepts it (section 24.1). The
software compatibility result is an explicit ``OK`` or ``PROBLEM`` for an
available hardware key (section 23.1), and the contact confirmation is
``Confirmed current`` or ``Needs external update``.

The key setup is configured once and stored in the database (section 23.2). The
configured name is the product label of a key, and the key's type decides which
checks apply, never the key number (section 23.3). The address path is part of
the key's identity (section 25.1), and no two keys may share one: the comparison
ignores surrounding whitespace, letter case, and the spelling of the hardened
marker, so ``m/48h/0h/0h/2h`` and ``m/48'/0'/0'/2'`` are the same path
(section 26.2).

The number of key slots and the multisig threshold are configurable, so the setup
carries ``threshold`` and ``key_count`` and the key numbers are bounded by that
count (section 31 point 7). Both fields are optional: a payload without them
keeps the 2-of-3 default, so an older client that only sends the keys keeps
working, and the bounds are enforced here rather than by a database CHECK.

The model is the optional model or service label of a key. It is documentation
only: it is not a wallet software choice, it is not part of the alert source, and
it is not part of the key's identity, so it is never locked. An empty value means
"not recorded" (section 31 point 5).

``available`` is always recorded (section 22). When the key was not available,
the wallet software and the security statuses are not recorded either, so they
may be left out of the payload.

The address path is recorded by the user and compared with the stored one by the
server, which sets ``address_path_verified`` and never takes it from the client
(section 25.1). A path that does not match makes the key uncheckable, which is
treated exactly like an unavailable key.

The wallet software choices are the settings list and the name of every
configured cloud key (section 25.4), and the settings, the key rotation and the
alert acknowledgements have their own payloads (sections 25.2, 25.3, 25.4 and
26.4). A rotation replaces the key, so it requires a new, unique address path,
and an acknowledgement records the action that closed the alert instead of a free
reason (sections 26.3 and 26.4).

The type is part of the identity of a key, and the setup locks it. A rotation
replaces the key with a new one, so the replacement may carry the other type, and
a key that becomes a cloud key may not take a name the wallet software list
already holds (section 28).

The BIP327/SLIP39 results are gone, together with the rest of that function
(section 24.2).
"""

from datetime import date

from alerts import ALERT_CODES, CLOSING_ACTIONS
from database import KEY_COUNT, MAX_KEY_COUNT, MIN_KEY_COUNT, MIN_THRESHOLD

# Software compatibility requires an active choice, so "not assessed" is not
# submittable for a new registration (section 23.1).
COMPATIBILITY_STATUSES = ("OK", "PROBLEM")
VERIFICATION_STATUSES = ("OK", "PROBLEM")
SECURITY_STATUSES = ("SECURE", "PATCHED", "VULNERABLE", "COMPROMISED")
CONTACT_STATUSES = ("Confirmed current", "Needs external update")
KEY_TYPES = ("hardware", "cloud")
MAX_KEY_NAME_LENGTH = 60
MAX_MODEL_LENGTH = 60
MAX_VERSION_LENGTH = 100
MAX_PATH_LENGTH = 200
MAX_NOTES_LENGTH = 2000
MAX_COMMENTS_LENGTH = 4000
MAX_SOURCE_LENGTH = 200
# The hardened marker of a BIP32 path is written with an apostrophe or with
# ``h``, and the two name the same derivation path, so the uniqueness comparison
# folds them together. ``casefold`` has already lowered an ``H`` by then, so only
# ``h`` needs mapping. The stored value is never rewritten: the path is free text
# and an existing row keeps the spelling the user recorded (section 26.2).
HARDENED_MARKER_FOLD = str.maketrans({"h": "'"})


class ValidationError(ValueError):
    """Raised when a payload does not match the expected shape."""


class DuplicateAddressPath(ValidationError):
    """Raised when an address path already belongs to another key.

    The settings answer this with ``409``, while the setup and the rotation
    answer ``400`` (section 26.2), so the two are kept apart here instead of
    being told apart by their message text.
    """


class WalletSoftwareNameInUse(ValidationError):
    """Raised when a rotation would make a key a cloud key under a taken name.

    A cloud key offers its own name as a wallet software choice, and the settings
    list holds the other choices, so the same name cannot be both. The rotation
    answers this with ``409``, like a locked or duplicate address path, and the
    user has to remove the list entry first (sections 25.4 and 28).
    """


def next_check_due(checked_at):
    """Return the check date one calendar year later, clamping 29 February."""
    checked = date.fromisoformat(checked_at)
    try:
        return checked.replace(year=checked.year + 1).isoformat()
    except ValueError:
        return checked.replace(year=checked.year + 1, day=28).isoformat()


def validate_multisig_settings(payload):
    """Return the normalized ``(threshold, key_count)`` of the single setup.

    Both fields are optional. A payload without them keeps the 2-of-3 default
    the app was built for, so an older client that only sends the keys keeps
    working, and the stored setup shape is unchanged. The bounds are enforced
    here rather than by a database CHECK, the same way the address path is
    handled (section 31 point 7).
    """
    if not isinstance(payload, dict):
        raise ValidationError("payload must be a JSON object")
    key_count = _multisig_key_count(payload.get("key_count"))
    threshold = _multisig_threshold(payload.get("threshold"), key_count)
    return threshold, key_count


def validate_key_setup(payload):
    """Return the normalized key setup for the configured key slots.

    The user names each key, picks its type, records its address path, and may
    record its model, and all of it is locked after the setup is saved except the
    name and the model (sections 23.2, 25.1 and 31.5). The names must be
    non-empty and unique, compared without regard to case. The address paths must
    be unique as well, so no two keys share one, because the path is part of the
    identity of a key, and two spellings of the same derivation path count as the
    same one (section 26.2). The number of keys has to match the setup's
    ``key_count``, which defaults to the 2-of-3 shape when it is left out
    (section 31 point 7).
    """
    if not isinstance(payload, dict):
        raise ValidationError("payload must be a JSON object")

    entries = payload.get("keys")
    if not isinstance(entries, list):
        raise ValidationError("keys must be a list")
    _, key_count = validate_multisig_settings(payload)
    if len(entries) != key_count:
        raise ValidationError(f"exactly {key_count} keys must be configured")

    normalized = []
    numbers = set()
    names = set()
    paths = {}
    for entry in entries:
        if not isinstance(entry, dict):
            raise ValidationError("each key must be an object")
        number = entry.get("key_number")
        if isinstance(number, bool) or number not in range(1, key_count + 1):
            raise ValidationError(f"key_number must be between 1 and {key_count}")
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

        address_path = _required_path(entry.get("address_path"), "address_path")
        folded = _path_key(address_path)
        if folded in paths:
            raise ValidationError(
                f"the address path is already used by key {paths[folded][0]}: "
                f"{paths[folded][1]}"
            )
        paths[folded] = (number, name)

        normalized.append({
            "key_number": number,
            "name": name,
            "type": key_type,
            "address_path": address_path,
            "model": _model(entry.get("model")),
        })

    return sorted(normalized, key=lambda entry: entry["key_number"])


def validate_health_check(payload, keys, software_names=()):
    """Return a normalized single-key health check ready for storage.

    ``software_names`` is the wallet software list from the settings, which
    completes the choices together with the configured cloud key names
    (section 25.4).
    """
    if not isinstance(payload, dict):
        raise ValidationError("payload must be a JSON object")

    entry = payload.get("key_check")
    if not isinstance(entry, dict):
        raise ValidationError("key_check must be an object")

    key = _select_key(entry.get("key_id"), keys)
    checked_at = _date(payload.get("checked_at"), "checked_at")
    available = _availability(entry.get("available"))
    # The server compares the recorded path with the stored one and derives the
    # verification result from that (section 25.1).
    address_path, mismatch = _address_path(entry.get("address_path"), key, available)
    # A key that was not available and a key whose address path does not match
    # are both uncheckable: nothing else about them can be recorded
    # (sections 22 and 25.1).
    uncheckable = available == 0 or mismatch
    wallet_software = _wallet_software(
        payload.get("wallet_software"), key, keys, software_names, uncheckable
    )

    return {
        "checked_at": checked_at,
        "next_check_due": next_check_due(checked_at),
        "wallet_software": wallet_software,
        "software_version": _text(
            payload.get("software_version"), "software_version", MAX_VERSION_LENGTH
        ),
        "software_compatibility_status": _compatibility_status(
            payload.get("software_compatibility_status"), key, uncheckable
        ),
        "software_comments": _text(
            payload.get("software_comments"), "software_comments", MAX_NOTES_LENGTH
        ),
        "contact_info_verified": _contact_status(payload.get("contact_info_verified")),
        "comments": _text(payload.get("comments"), "comments", MAX_COMMENTS_LENGTH),
        "key_check": _key_check(entry, key, available, address_path, mismatch),
        "ai_security_checks": _ai_security_checks(
            payload.get("ai_security_checks"), key, wallet_software, uncheckable
        ),
    }


def validate_key_settings(payload, keys):
    """Return the normalized settings of one key.

    The name and the model are only labels and may be changed at any time; the
    address path is part of the key's identity and may only be changed while the
    key has no saved check, which the caller decides (sections 25.1, 25.2 and
    31.5). The type is never part of the payload: it only changes when the key is
    rotated (section 28). A path that another key already has is refused
    (section 26.2).
    """
    if not isinstance(payload, dict):
        raise ValidationError("payload must be a JSON object")

    key = _select_key(payload.get("key_id"), keys)
    name = _key_name(payload.get("name"))
    if any(
        other["id"] != key["id"] and other["name"].casefold() == name.casefold()
        for other in keys
    ):
        raise ValidationError("key names must be unique")
    address_path = _required_path(payload.get("address_path"), "address_path")
    _ensure_unique_path(address_path, keys, key["id"])
    return {
        "key_id": key["id"],
        "name": name,
        "address_path": address_path,
        "model": _model(payload.get("model")),
    }


def validate_wallet_software(payload, keys):
    """Return the normalized wallet software list from the settings.

    The list is stored whole, so it is validated as a whole: at least one name,
    every name non-empty, no repeated name, and no name that already comes from
    a configured cloud key (section 25.4).
    """
    if not isinstance(payload, dict):
        raise ValidationError("payload must be a JSON object")

    entries = payload.get("wallet_software")
    if not isinstance(entries, list):
        raise ValidationError("wallet_software must be a list")
    if not entries:
        raise ValidationError("at least one wallet software name is required")

    cloud_names = {
        key["name"].casefold() for key in keys if key["type"] == "cloud"
    }
    names = []
    seen = set()
    for entry in entries:
        name = _key_name(entry)
        folded = name.casefold()
        if folded in seen:
            raise ValidationError("wallet software names must be unique")
        if folded in cloud_names:
            raise ValidationError(
                "a configured cloud key already provides this wallet software name"
            )
        seen.add(folded)
        names.append(name)
    return names


def validate_rotation(payload, keys, key_id, software_names=()):
    """Return the confirmed rotation of one key.

    The user confirms that the key has been replaced, chooses whether the name
    stays or changes, records the new address path, and may pick the other type
    for the replacement (section 28). The path must change, because the rotation
    replaces the key and the path is its identity, and it must not belong to
    another key (sections 26.2 and 26.3). The model may be recorded with the
    replacement as well (section 31 point 5).

    ``software_names`` is the wallet software list from the settings, which the
    type change needs: a key that becomes a cloud key offers its own name as a
    wallet software choice, so a name the list already holds is refused with
    ``WalletSoftwareNameInUse`` (sections 25.4 and 28).
    """
    if not isinstance(payload, dict):
        raise ValidationError("payload must be a JSON object")

    key = _select_key(key_id, keys)
    if payload.get("replaced") is not True:
        raise ValidationError("the replacement of the key must be confirmed")

    keep_name = payload.get("keep_name")
    if not isinstance(keep_name, bool):
        raise ValidationError("keep_name must be true or false")

    name = None
    if not keep_name:
        name = _key_name(payload.get("name"))
        if any(
            other["id"] != key["id"] and other["name"].casefold() == name.casefold()
            for other in keys
        ):
            raise ValidationError("key names must be unique")

    # The replacement may carry the other type, and the name it ends up with is
    # the one the wallet software list has to stay clear of (section 28).
    key_type = _rotation_type(payload.get("type"), key, name or key["name"], software_names)

    address_path = _required_path(payload.get("address_path"), "address_path")
    if _path_key(address_path) == _path_key(key.get("address_path")):
        raise ValidationError(
            "the address path must change when the key is rotated"
        )
    _ensure_unique_path(address_path, keys, key["id"])
    return {
        "key_id": key["id"],
        "keep_name": keep_name,
        "name": name,
        "type": key_type,
        "address_path": address_path,
        "model": _model(payload.get("model")),
    }


def validate_acknowledgement(payload):
    """Return the normalized acknowledgement of one alert.

    An acknowledgement closes a single alert, identified by its code and its
    source, and records the action that closed it, which is stored as the reason
    (sections 25.3 and 26.4). Only the actions the acknowledgement itself
    performs are accepted here: a rotation goes through the rotation endpoint,
    because it requires a new, unique address path (section 26.3). Whether the
    action belongs to the alert is checked against the alert itself.
    """
    if not isinstance(payload, dict):
        raise ValidationError("payload must be a JSON object")

    code = payload.get("code")
    if code not in ALERT_CODES:
        raise ValidationError("code is not a known alert")
    source = _text(payload.get("source"), "source", MAX_SOURCE_LENGTH)
    if source is None:
        raise ValidationError("source is required")
    action = payload.get("action")
    if action not in CLOSING_ACTIONS:
        raise ValidationError("action is not a closing action for an alert")
    return {"code": code, "source": source, "action": action}


def _multisig_key_count(value):
    """Return the number of key slots, defaulting to the 2-of-3 shape."""
    if value is None or value == "":
        return KEY_COUNT
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValidationError("key_count must be a whole number")
    if not MIN_KEY_COUNT <= value <= MAX_KEY_COUNT:
        raise ValidationError(
            f"key_count must be between {MIN_KEY_COUNT} and {MAX_KEY_COUNT}"
        )
    return value


def _multisig_threshold(value, key_count):
    """Return the multisig threshold, defaulting to two of the key slots.

    A threshold of 1 is allowed, because the user chooses it and the app puts no
    meaning into the number (section 31 point 7).
    """
    if value is None or value == "":
        return min(2, key_count)
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValidationError("threshold must be a whole number")
    if not MIN_THRESHOLD <= value <= key_count:
        raise ValidationError(
            f"threshold must be between {MIN_THRESHOLD} and {key_count}"
        )
    return value


def _model(value):
    """Return the optional model or service label, or None when it is empty.

    The field is documentation only, so it is trimmed and bounded like the key
    name, and an empty value means "not recorded" (section 31 point 5).
    """
    if value is None:
        return None
    if not isinstance(value, str):
        raise ValidationError("model must be text")
    model = value.strip()
    if not model:
        return None
    if len(model) > MAX_MODEL_LENGTH:
        raise ValidationError("model is too long")
    return model


def _rotation_type(value, key, name, software_names):
    """Return the type the key has after the rotation.

    The type is part of the identity of the key, so the setup locks it and only a
    rotation, which replaces the key with a new one, may pick the other one. A
    value that is left out keeps the type the key has now (section 28).

    A key that ends up as a cloud key offers its own name as a wallet software
    choice, and the settings list holds the other choices, so the same name
    cannot be both: a name the list already holds is refused, and the user has to
    remove that entry first (section 25.4).
    """
    if value is None:
        return key["type"]
    if value not in KEY_TYPES:
        raise ValidationError("key type must be hardware or cloud")
    if value == "cloud":
        folded = name.casefold()
        for entry in software_names:
            if entry.strip().casefold() == folded:
                raise WalletSoftwareNameInUse(
                    f"the wallet software list already holds the name {name}; "
                    "remove that entry before this key becomes a cloud key"
                )
    return value


def _key_name(value):
    """Return a configured key name, which must be non-empty text."""
    if not isinstance(value, str):
        raise ValidationError("key name must be text")
    name = value.strip()
    if not name:
        raise ValidationError("key name must not be empty")
    if len(name) > MAX_KEY_NAME_LENGTH:
        raise ValidationError("key name is too long")
    return name


def _required_path(value, field):
    """Return a non-empty address path.

    The path is a public derivation path and holds no secret (section 25.1).
    """
    if not isinstance(value, str):
        raise ValidationError(f"{field} must be text")
    path = value.strip()
    if not path:
        raise ValidationError(f"{field} must not be empty")
    if len(path) > MAX_PATH_LENGTH:
        raise ValidationError(f"{field} is too long")
    return path


def _path_key(path):
    """Return the canonical form of an address path, used for comparisons only.

    The comparison ignores surrounding whitespace, letter case, and the spelling
    of the hardened marker, because ``m/48h/0h/0h/2h`` and ``m/48'/0'/0'/2'`` are
    the same derivation path. Folding only the comparison key keeps the stored
    value exactly as the user recorded it (section 26.2).
    """
    return (path or "").strip().casefold().translate(HARDENED_MARKER_FOLD)


def _ensure_unique_path(path, keys, key_id):
    """Reject an address path that another key already has (section 26.2).

    The comparison uses the canonical form ``_path_key`` gives, so two paths that
    differ only in case, in surrounding whitespace, or in the spelling of the
    hardened marker count as the same one. The message names the key that already
    has the path.
    """
    folded = _path_key(path)
    for other in keys:
        if other["id"] == key_id:
            continue
        if _path_key(other.get("address_path")) == folded:
            raise DuplicateAddressPath(
                f"the address path is already used by key {other['key_number']}: "
                f"{other['name']}"
            )


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


def _address_path(value, key, available):
    """Return the recorded address path and whether it matches the key.

    The recorded path is compared with the path stored for the key in the
    canonical form ``_path_key`` gives: equal gives ``OK``, different gives
    ``PROBLEM`` (sections 25.1 and 26.2). A key that was not available records no
    path at all, so no mismatch is reported for it.
    """
    if available == 0:
        return None, False
    submitted = _text(value, "address_path", MAX_PATH_LENGTH)
    return submitted, _path_key(submitted) != _path_key(key.get("address_path"))


def _wallet_software_choices(keys, software_names):
    """Return the wallet software choices.

    The settings list and the name of every configured cloud key. A hardware key
    name is never a software choice (sections 23.3 and 25.4).
    """
    cloud_names = (key["name"] for key in keys if key["type"] == "cloud")
    return tuple(dict.fromkeys((*software_names, *cloud_names)))


def _wallet_software(value, key, keys, software_names, uncheckable):
    """Return the selected wallet software.

    A cloud key records its own name, because the provider is the software for
    that key (section 23.3). A key that could not be checked records no software,
    so the field must be left out then (sections 22 and 25.1).
    """
    if value is None or value == "":
        if uncheckable:
            return None
        raise ValidationError("wallet_software is required when the key is available")
    if uncheckable:
        raise ValidationError(
            "wallet_software cannot be recorded when the key could not be checked"
        )
    if key["type"] == "cloud":
        if value != key["name"]:
            raise ValidationError("a cloud key records its own name as the wallet software")
        return value
    if value not in _wallet_software_choices(keys, software_names):
        raise ValidationError(
            "wallet_software must be one of the configured wallet software names"
        )
    return value


def _compatibility_status(value, key, uncheckable):
    """Return the software compatibility result.

    A key that could not be checked keeps the derived ``NOT_ASSESSED`` value,
    which is the only place it is allowed (sections 22, 24.1 and 25.1). A cloud
    key derives its result from availability (section 20), and an available
    hardware key requires an active ``OK`` or ``PROBLEM`` (section 23.1).
    """
    if uncheckable:
        if value not in (None, "", "NOT_ASSESSED"):
            raise ValidationError(
                "software_compatibility_status cannot be recorded "
                "when the key could not be checked"
            )
        return "NOT_ASSESSED"
    if key["type"] == "cloud":
        if value not in (None, "", "OK"):
            raise ValidationError(
                "software_compatibility_status is derived for the cloud key"
            )
        return "OK"
    return _status(value, "software_compatibility_status", COMPATIBILITY_STATUSES)


def _contact_status(value):
    """Return the contact confirmation for the selected key's holder.

    The confirmation is required, also when the key could not be checked, because
    the question is still asked (section 24.1). Only the status is recorded,
    never names, addresses, phone numbers, or credentials (section 23.1).
    """
    if value is None or value == "":
        raise ValidationError("contact_info_verified is required")
    return _status(value, "contact_info_verified", CONTACT_STATUSES)


def _require_nothing_recorded(entries, field):
    """Reject results for a key that could not be checked (sections 22 and 25.1)."""
    if entries is None or entries == []:
        return
    raise ValidationError(f"{field} cannot be recorded when the key could not be checked")


def _expected_labels(key, wallet_software):
    """Return the labels a submission records, without duplicates.

    The security statuses are recorded for the selected key, by its configured
    name, and for the selected wallet software (section 23.3). A cloud key that
    is named after its own software therefore contributes one label only.
    """
    return tuple(dict.fromkeys((key["name"], wallet_software)))


def _key_check(entry, key, available, address_path, mismatch):
    """Return the normalized check for the selected key."""
    check = {
        "key_id": key["id"],
        "available": available,
        "hardware_works": None,
        "firmware_version": None,
        "seed_backup_verified": None,
        "address_path_verified": None,
        "address_path": None,
        "comments": _text(entry.get("comments"), "comments", MAX_NOTES_LENGTH),
    }
    if available == 0:
        # The remaining checks could not be performed, so nothing is recorded
        # (section 22).
        return check
    if mismatch:
        # The recorded path does not match the key, so the key could not be
        # checked: the path itself, the key note, the contact confirmation and
        # the overall comment are kept, while everything else stays empty
        # (section 25.1).
        check["address_path"] = address_path
        check["address_path_verified"] = "PROBLEM"
        return check

    if key["type"] == "hardware":
        # Hardware works requires an active Yes or No, so leaving it out is a
        # 400 (section 24.1).
        check["hardware_works"] = _flag_required(
            entry.get("hardware_works"), "hardware_works"
        )
        check["firmware_version"] = _text(
            entry.get("firmware_version"), "firmware_version", MAX_VERSION_LENGTH
        )
        check["seed_backup_verified"] = _verification(
            entry.get("seed_backup_verified"), "seed_backup_verified"
        )
    check["address_path"] = address_path
    # The comparison matched, so the verification result is OK (section 25.1).
    check["address_path_verified"] = "OK"
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


def _verification(value, field):
    """Return OK/PROBLEM, requiring an active choice."""
    if value is None or value == "":
        raise ValidationError(f"{field} is required when the key is available")
    return _status(value, field, VERIFICATION_STATUSES)


def _flag(value, field):
    """Return 0 or 1, or None when the value was left out."""
    if value is None or value == "":
        return None
    if isinstance(value, bool):
        return int(value)
    if value in (0, 1):
        return int(value)
    raise ValidationError(f"{field} must be 0 or 1")


def _flag_required(value, field):
    """Return 0 or 1, requiring an active choice (section 24.1)."""
    flag = _flag(value, field)
    if flag is None:
        raise ValidationError(f"{field} is required when the key is available")
    return flag


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


def _ai_security_checks(entries, key, wallet_software, uncheckable):
    """Return the security status rows for the selected key and wallet software."""
    if uncheckable:
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
