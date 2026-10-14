"""Alert rules derived from saved health checks.

The rules follow the follow-up requirements for the annual health check. The
application only reports these alerts; it never performs the follow-up actions
itself.

One saved check covers one key. A key that was not available produces a single
critical alert, because the remaining checks for that key could not be
performed. A recorded address path that does not match the key is treated the
same way, with its own code, so it is never merged with a real unavailable key
(section 25.1).

Every alert code has its own closing actions (section 26.4). A rotation replaces
the key and is confirmed in the settings, while the other actions close the
alert where it is shown. The software an alert is about is named, so the link,
the button, and the removal point at the right settings entry (section 26.7).
``collect_alerts`` builds the alerts of every saved check, merges them, and
leaves out the acknowledged ones, which is what the dashboard shows
(sections 21 and 25.3).

Every message says what is wrong, which key or software it is about, and what
closes the alert (section 32.3). The source the alert carries names the key or
the software, so the message itself does not repeat that name; the one exception
is the cloud-key form of ``software_incompatible``, whose source is the key while
the message has to name the software.

Two alerts belong to the checked key although they are not about the key itself
(section 27). The contact alert is one of them, so it blocks the key until the
user has updated the contact details externally. The other one is a wallet
software that no longer supports the hardware, when that software is the name of
a configured cloud key: such a name can never be removed from the settings, so
that form of the alert asks for a new hardware wallet instead.

An alert without an action is a bug, not a state the user can reach: the key
would be locked with no way out (section 26.1). ``_alert`` therefore refuses to
build one.
"""

CRITICAL = "critical"
INFO = "info"

# The actions that close an alert (section 26.4). A rotation replaces the key and
# is performed in the settings; the other actions close the alert where it is
# shown, after the user has confirmed the action.
ROTATE = "rotate"
REPLACE_HARDWARE = "replace_hardware"
REMOVE_SOFTWARE = "remove_software"
IGNORE = "ignore"
CONTACT_UPDATED = "contact_updated"
# The actions the acknowledgement endpoint performs. A rotation is not one of
# them: it goes through POST /api/keys/<id>/rotate, which requires a new address
# path, so an alert that only offers a rotation cannot be closed by a plain
# acknowledgement (sections 26.1, 26.3 and 26.4).
CLOSING_ACTIONS = frozenset({
    REPLACE_HARDWARE,
    REMOVE_SOFTWARE,
    IGNORE,
    CONTACT_UPDATED,
})
ALERT_ACTIONS = frozenset({ROTATE}) | CLOSING_ACTIONS

# Every alert code the app can raise. ``cloud_provider_problem`` and
# ``address_verification_failed`` are gone: the first could not be triggered from
# the form, and the second was replaced by ``address_path_mismatch``
# (section 25.3).
ALERT_CODES = frozenset({
    "key_unavailable",
    "address_path_mismatch",
    "hardware_failure",
    "seed_backup_problem",
    "software_incompatible",
    "security_vulnerable",
    "security_compromised",
    "contact_info_unconfirmed",
})
# The codes a rotation closes. A security code is only closed by a rotation when
# its source is the key itself, because a problem in the software the key runs
# with is not resolved by replacing the key (sections 25.3 and 26.4).
ROTATION_CODES = frozenset({
    "key_unavailable",
    "address_path_mismatch",
    "hardware_failure",
    "seed_backup_problem",
    "security_vulnerable",
    "security_compromised",
})
_SECURITY_CODES = frozenset({"security_vulnerable", "security_compromised"})
_SEVERITY_ORDER = {CRITICAL: 0, INFO: 1}

_KEY_UNAVAILABLE_MESSAGE = (
    "This key was not available, so its checks could not be recorded. "
    "Rotate the key to close this alert."
)
_ADDRESS_PATH_MISMATCH_MESSAGE = (
    "The recorded address path does not match the stored path for this key, so "
    "it could not be checked. Rotate the key to close this alert."
)
_HARDWARE_FAILURE_MESSAGE = (
    "The hardware wallet does not work. Replace the hardware and restore the "
    "same seed, or rotate the key, to close this alert."
)
_SEED_BACKUP_MESSAGE = (
    "The seed backup is missing or damaged, so the key cannot be trusted. "
    "Rotate the key to close this alert."
)
# The software that produced the result is named by the alert itself, so this
# message covers the software in general (section 26.7).
_SOFTWARE_INCOMPATIBLE_MESSAGE = (
    "This wallet software no longer supports the hardware. Add another wallet "
    "software in the settings, then remove this one to close the alert."
)
# When the wallet software is the name of a configured cloud key, it can never be
# removed from the settings, so the alert asks for a new hardware wallet instead
# (section 27). The source of that form is the key and not the software, so the
# message names the software it is about.
_SOFTWARE_INCOMPATIBLE_KEY_MESSAGE = (
    "{software} no longer supports the hardware for this key. Replace the "
    "hardware wallet and restore the same seed, then close this alert."
)
# A security alert has two forms, and they are closed by different actions, so
# each form says what closes it (section 32.3).
_VULNERABLE_KEY_MESSAGE = (
    "The security status for this key is VULNERABLE. Rotate the key, or close "
    "this alert without action."
)
_VULNERABLE_SOFTWARE_MESSAGE = (
    "The security status for this wallet software is VULNERABLE. Remove this "
    "software from the settings, or close this alert without action."
)
_COMPROMISED_KEY_MESSAGE = (
    "The security status for this key is COMPROMISED. Rotate the key to close "
    "this alert."
)
_COMPROMISED_SOFTWARE_MESSAGE = (
    "The security status for this wallet software is COMPROMISED. Remove this "
    "software from the settings to close this alert."
)
# The contact alert belongs to the checked key, and the source it carries names
# that key, so the message points at the key without repeating the name
# (section 27).
_CONTACT_MESSAGE = (
    "The contact details for this key need an external update. Update them in "
    "your external documentation, then close this alert."
)
# A saved check that predates the software column has no name to point at, so the
# alert falls back to this label and offers the settings link only.
_SOFTWARE_SOURCE = "Software compatibility"
# The stored contact status that asks for an update of the user's own records
# (section 23.1).
_CONTACT_NEEDS_UPDATE = "Needs external update"


def build_alerts(record, cloud_names=()):
    """Return the active alerts for one saved health check.

    Critical alerts are listed before informational ones; the order within each
    severity follows the checklist order. ``cloud_names`` holds the configured
    names of the cloud keys, because such a name is also a wallet software choice
    and can never be removed from the settings (section 27).
    """
    key_checks = record.get("key_checks") or ()
    key_ids = {}
    for key_check in key_checks:
        name = key_check.get("name")
        if name is not None:
            key_ids.setdefault(name, key_check.get("key_id"))

    alerts = []
    for key_check in key_checks:
        alerts.extend(_key_alerts(key_check))
    alerts.extend(_software_alerts(record, cloud_names))
    for security_check in record.get("ai_security_checks") or ():
        alerts.extend(_security_alerts(security_check, key_ids))
    alerts.extend(_contact_alerts(record))
    alerts.sort(key=lambda alert: _SEVERITY_ORDER[alert["severity"]])
    return alerts


def collect_alerts(records, acknowledgements=(), cloud_names=()):
    """Return the merged alerts of every saved check, critical and newest first.

    Each alert carries the ``check_id`` and ``checked_at`` of the check it came
    from, so the dashboard can show where a warning originated. Identical alerts
    (same ``code`` and ``source``) are merged, and only the newest one is kept,
    with its own date. Critical alerts are listed first, then the newest check
    first inside each severity.

    An acknowledged alert is left out until a newer check for the same code and
    source raises it again (section 25.3). An alert that belongs to a key is
    identified by its key instead, so a rename does not open a closed alert again
    (section 27).
    """
    tagged = []
    for record in records:
        for alert in build_alerts(record, cloud_names):
            tagged.append({
                **alert,
                "check_id": record.get("id"),
                "checked_at": record.get("checked_at"),
            })

    # Newest first, so the first alert of a code and source pair is the newest.
    tagged.sort(key=_recency_key, reverse=True)
    newest = {}
    for alert in tagged:
        newest.setdefault((alert["code"], alert["source"]), alert)

    merged = [
        alert
        for alert in newest.values()
        if not _is_acknowledged(alert, acknowledgements)
    ]
    # A stable sort, so the newest-first order stays inside each severity.
    merged.sort(key=lambda alert: _SEVERITY_ORDER[alert["severity"]])
    return merged


def rotation_alert_targets(records, key, cloud_names=()):
    """Return the (code, source) pairs that rotating one key closes.

    A rotation closes the alerts that this key's own checks raised and that a
    replacement resolves (sections 25.3 and 26.4). A security alert whose source
    is the software the key runs with is not closed by the rotation, because that
    problem is about the software and not about the key.
    """
    targets = []
    for record in records:
        if not _record_covers_key(record, key):
            continue
        for alert in build_alerts(record, cloud_names):
            if alert["code"] not in ROTATION_CODES:
                continue
            if alert["code"] in _SECURITY_CODES and alert.get("key_id") != key["id"]:
                continue
            targets.append((alert["code"], alert["source"]))
    # One entry per pair, in the order the checks were read.
    return list(dict.fromkeys(targets))


def software_alert_targets(records, acknowledgements, names, cloud_names=()):
    """Return the (code, source, key_id) triples that removing software closes.

    Removing a wallet software from the settings closes the alerts the software
    itself raised: software that no longer supports the hardware, and a security
    status the software got (sections 26.4 and 26.7). Only the alerts that are
    still open are returned, so removing a name never writes an acknowledgement
    for an alert that is already closed. The key id is the key the alert belonged
    to, and it is None for a software alert raised by the settings list
    (section 27).
    """
    folded = _folded_names(names)
    targets = []
    for alert in collect_alerts(records, acknowledgements, cloud_names):
        software = alert.get("software")
        if not software or software.casefold() not in folded:
            continue
        targets.append((alert["code"], alert["source"], alert.get("key_id")))
    # One entry per triple, so a name is closed once.
    return list(dict.fromkeys(targets))


def _folded_names(names):
    """Return names compared without surrounding spaces or letter case."""
    return {name.strip().casefold() for name in names or () if isinstance(name, str)}


def _checked_key(record):
    """Return the key check a record was made for, or None.

    A record saved before section 19 can hold up to three key checks, one per
    key. The first one is the key the submission was made for, which is the key
    the contact question and the recorded wallet software belong to
    (section 27).
    """
    key_checks = record.get("key_checks") or ()
    return key_checks[0] if key_checks else None


def _key_source(key_check):
    """Return the label a key alert uses for one key."""
    return f"Key {key_check.get('key_number')}: {key_check.get('name')}"


def _record_covers_key(record, key):
    """Return True when a saved check recorded this key."""
    return any(
        key_check.get("key_id") == key["id"]
        for key_check in record.get("key_checks") or ()
    )


def _is_acknowledged(alert, acknowledgements):
    """Return True while an acknowledgement still covers this alert.

    An alert that belongs to a key is hidden by that key, so the name the key has
    now cannot open a closed alert again. An alert without a key keeps matching
    on its source (section 27). The acknowledgement stores the newest check that
    raised the alert when it was closed, so a newer check, which always has a
    higher id, raises the alert again (section 25.3).
    """
    check_id = alert.get("check_id")
    key_id = alert.get("key_id")
    for acknowledgement in acknowledgements:
        if acknowledgement.get("code") != alert["code"]:
            continue
        if key_id is not None:
            if acknowledgement.get("key_id") != key_id:
                continue
        elif acknowledgement.get("source") != alert["source"]:
            continue
        acknowledged_id = acknowledgement.get("check_id")
        if check_id is None or acknowledged_id is None:
            # Without a check id there is nothing to compare, so the alert is
            # kept rather than hidden by accident.
            continue
        if check_id <= acknowledged_id:
            return True
    return False


def _recency_key(alert):
    """Return a sortable key for the check an alert came from."""
    return (alert.get("checked_at") or "", alert.get("check_id") or 0)


def _alert(code, severity, source, message, actions, key_id=None, software=None):
    """Return one alert, and refuse to build one without a closing action.

    Every alert has to stay closable, or the key would be locked with no way out
    (section 26.1). ``software`` names the wallet software the alert is about, so
    the settings can remove the right entry, and it is None for every other alert
    (section 26.7).
    """
    actions = list(actions)
    if not actions:
        raise ValueError(f"alert {code} must offer at least one closing action")
    return {
        "code": code,
        "severity": severity,
        "source": source,
        "message": message,
        "actions": actions,
        "key_id": key_id,
        "software": software,
    }


def _key_alerts(key_check):
    """Return the alerts for one key check.

    A key alert is closed by replacing the key. A hardware failure may also be
    closed by replacing the hardware wallet, because the key and its address path
    stay the same when the same seed is restored on a new device (section 26.4).
    """
    source = _key_source(key_check)
    key_id = key_check.get("key_id")
    if key_check.get("available") == 0:
        # The remaining checks for this key could not be performed.
        return [_alert(
            "key_unavailable",
            CRITICAL,
            source,
            _KEY_UNAVAILABLE_MESSAGE,
            (ROTATE,),
            key_id,
        )]

    alerts = []
    if key_check.get("hardware_works") == 0:
        alerts.append(_alert(
            "hardware_failure",
            CRITICAL,
            source,
            _HARDWARE_FAILURE_MESSAGE,
            (ROTATE, REPLACE_HARDWARE),
            key_id,
        ))
    if key_check.get("seed_backup_verified") == "PROBLEM":
        alerts.append(_alert(
            "seed_backup_problem",
            CRITICAL,
            source,
            _SEED_BACKUP_MESSAGE,
            (ROTATE,),
            key_id,
        ))
    if key_check.get("address_path_verified") == "PROBLEM":
        # The recorded path does not match the key, so the key could not be
        # checked. Its own code keeps it apart from a real unavailable key
        # (section 25.1).
        alerts.append(_alert(
            "address_path_mismatch",
            CRITICAL,
            source,
            _ADDRESS_PATH_MISMATCH_MESSAGE,
            (ROTATE,),
            key_id,
        ))
    return alerts


def _software_alerts(record, cloud_names):
    """Return the alert for software that no longer supports the hardware.

    The source is the software that produced the result, so the alert, the
    settings link, and the removal point at the right entry (section 26.7). When
    that software is the name of a configured cloud key, it can never be removed
    from the settings, so the alert belongs to the checked key and asks for a
    replacement of the hardware instead (section 27). That form carries no
    ``software``: there is no settings entry to remove, so a software removal
    must not be able to close it.
    """
    if record.get("software_compatibility_status") != "PROBLEM":
        return []
    software = (record.get("wallet_software") or "").strip() or None
    key_check = _checked_key(record)
    if (
        software is not None
        and software.casefold() in _folded_names(cloud_names)
        and key_check is not None
    ):
        return [_alert(
            "software_incompatible",
            CRITICAL,
            _key_source(key_check),
            _SOFTWARE_INCOMPATIBLE_KEY_MESSAGE.format(software=software),
            (REPLACE_HARDWARE,),
            key_check.get("key_id"),
        )]
    return [_alert(
        "software_incompatible",
        CRITICAL,
        software or _SOFTWARE_SOURCE,
        _SOFTWARE_INCOMPATIBLE_MESSAGE,
        (REMOVE_SOFTWARE,),
        software=software,
    )]


def _security_alerts(security_check, key_ids):
    """Return the alerts for one external security status.

    The source of a security alert is the provider. When that provider is the
    key's own configured name, the key is the source and a rotation closes the
    alert; otherwise the provider is the software the key runs with, so the alert
    names it and is closed by removing it from the settings (sections 25.3, 26.4
    and 26.7). A compromised key or software can never be ignored: the key must
    be replaced, and the software must be removed.
    """
    provider = security_check.get("provider")
    status = security_check.get("status")
    key_id = key_ids.get(provider)
    software = None if key_id is not None else provider

    if status == "VULNERABLE":
        if key_id is not None:
            message = _VULNERABLE_KEY_MESSAGE
            actions = (ROTATE, IGNORE)
        else:
            message = _VULNERABLE_SOFTWARE_MESSAGE
            actions = (REMOVE_SOFTWARE, IGNORE)
        return [_alert(
            "security_vulnerable",
            CRITICAL,
            provider,
            message,
            actions,
            key_id,
            software,
        )]
    if status == "COMPROMISED":
        if key_id is not None:
            message = _COMPROMISED_KEY_MESSAGE
            actions = (ROTATE,)
        else:
            message = _COMPROMISED_SOFTWARE_MESSAGE
            actions = (REMOVE_SOFTWARE,)
        return [_alert(
            "security_compromised",
            CRITICAL,
            provider,
            message,
            actions,
            key_id,
            software,
        )]
    return []


def _contact_alerts(record):
    """Return the alert for contact details that need an external update.

    The alert belongs to the checked key, so it blocks that key like every other
    key alert, and the source it carries names that key (section 27). Only the
    stored status is read; the app never stores contact details (section 23.1).
    """
    if record.get("contact_info_verified") != _CONTACT_NEEDS_UPDATE:
        return []
    key_check = _checked_key(record)
    if key_check is None:
        # Without a key there is nothing the alert could belong to, so no alert
        # is raised.
        return []
    return [_alert(
        "contact_info_unconfirmed",
        INFO,
        _key_source(key_check),
        _CONTACT_MESSAGE,
        (CONTACT_UPDATED,),
        key_check.get("key_id"),
    )]
