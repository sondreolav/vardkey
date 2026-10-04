"""Alert rules derived from saved health checks.

The rules follow the follow-up requirements for the annual health check. The
application only reports these alerts; it never performs the follow-up actions
itself.

One saved check covers one key. A key that was not available produces a single
critical alert, because the remaining checks for that key could not be
performed. A recorded address path that does not match the key is treated the
same way, with its own code, so it is never merged with a real unavailable key
(section 25.1).

Every alert names the actions that close it (section 25.3). A rotation replaces
the key, while a plain acknowledgement closes an alert until a newer check for
the same code and source raises it again. ``collect_alerts`` builds the alerts of
every saved check, merges them, and leaves out the acknowledged ones, which is
what the dashboard shows (sections 21 and 25.3).
"""

CRITICAL = "critical"
INFO = "info"

# The actions that can close an alert (section 25.3).
ROTATE = "rotate"
ACKNOWLEDGE = "acknowledge"

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
# with is not resolved by replacing the key (section 25.3).
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
    "This key was not available. Replace the key before continuing; "
    "the remaining checks for this key cannot be recorded."
)
_ADDRESS_PATH_MISMATCH_MESSAGE = (
    "The recorded address path does not match this key. Replace the key before "
    "continuing; the remaining checks for this key cannot be recorded."
)
# The stored contact status that asks for an update of the user's own records
# (section 23.1).
_CONTACT_NEEDS_UPDATE = "Needs external update"


def build_alerts(record):
    """Return the active alerts for one saved health check.

    Critical alerts are listed before informational ones; the order within each
    severity follows the checklist order.
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
    alerts.extend(_software_alerts(record))
    for security_check in record.get("ai_security_checks") or ():
        alerts.extend(_security_alerts(security_check, key_ids))
    alerts.extend(_contact_alerts(record))
    alerts.sort(key=lambda alert: _SEVERITY_ORDER[alert["severity"]])
    return alerts


def collect_alerts(records, acknowledgements=()):
    """Return the merged alerts of every saved check, critical and newest first.

    Each alert carries the ``check_id`` and ``checked_at`` of the check it came
    from, so the dashboard can show where a warning originated. Identical alerts
    (same ``code`` and ``source``) are merged, and only the newest one is kept,
    with its own date. Critical alerts are listed first, then the newest check
    first inside each severity.

    An acknowledged alert is left out until a newer check for the same code and
    source raises it again (section 25.3).
    """
    tagged = []
    for record in records:
        for alert in build_alerts(record):
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


def rotation_alert_targets(records, key):
    """Return the (code, source) pairs that rotating one key closes.

    A rotation closes the alerts that this key's own checks raised and that a
    replacement resolves (section 25.3). A security alert whose source is the
    software the key runs with is not closed by the rotation, because that
    problem is about the software and not about the key.
    """
    targets = []
    for record in records:
        if not _record_covers_key(record, key):
            continue
        for alert in build_alerts(record):
            if alert["code"] not in ROTATION_CODES:
                continue
            if alert["code"] in _SECURITY_CODES and alert.get("key_id") != key["id"]:
                continue
            targets.append((alert["code"], alert["source"]))
    # One entry per pair, in the order the checks were read.
    return list(dict.fromkeys(targets))


def _record_covers_key(record, key):
    """Return True when a saved check recorded this key."""
    return any(
        key_check.get("key_id") == key["id"]
        for key_check in record.get("key_checks") or ()
    )


def _is_acknowledged(alert, acknowledgements):
    """Return True while an acknowledgement still covers this alert.

    The acknowledgement stores the newest check that raised the alert when it was
    closed, so a newer check, which always has a higher id, raises the alert
    again (section 25.3).
    """
    check_id = alert.get("check_id")
    for acknowledgement in acknowledgements:
        if acknowledgement.get("code") != alert["code"]:
            continue
        if acknowledgement.get("source") != alert["source"]:
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


def _alert(code, severity, source, message, actions, key_id=None):
    return {
        "code": code,
        "severity": severity,
        "source": source,
        "message": message,
        "actions": list(actions),
        "key_id": key_id,
    }


def _key_alerts(key_check):
    """Return the alerts for one key check."""
    source = f"Key {key_check.get('key_number')}: {key_check.get('name')}"
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
            "The hardware does not work. Test the seed backup on another compatible device.",
            (ROTATE, ACKNOWLEDGE),
            key_id,
        ))
    if key_check.get("seed_backup_verified") == "PROBLEM":
        alerts.append(_alert(
            "seed_backup_problem",
            CRITICAL,
            source,
            "The seed backup is missing or damaged. Activate PROTOCOL 3: key loss.",
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


def _software_alerts(record):
    """Return the alert for software that no longer supports the hardware."""
    if record.get("software_compatibility_status") == "PROBLEM":
        return [_alert(
            "software_incompatible",
            CRITICAL,
            "Software compatibility",
            "The software no longer supports the hardware. Add alternative software "
            "in the settings, then close this alert.",
            (ACKNOWLEDGE,),
        )]
    return []


def _security_alerts(security_check, key_ids):
    """Return the alerts for one external security status.

    The source of a security alert is the provider. When that provider is the
    key's own configured name, the key is the source and a rotation closes the
    alert; otherwise the provider is the software the key runs with, and only a
    plain acknowledgement closes it (section 25.3).
    """
    provider = security_check.get("provider")
    status = security_check.get("status")
    key_id = key_ids.get(provider)

    if status == "VULNERABLE":
        actions = (ROTATE, ACKNOWLEDGE) if key_id is not None else (ACKNOWLEDGE,)
        return [_alert(
            "security_vulnerable",
            CRITICAL,
            provider,
            "Security status VULNERABLE: the firmware or security problem must be followed up.",
            actions,
            key_id,
        )]
    if status == "COMPROMISED":
        # A compromised key must be replaced, so closing is not enough there.
        actions = (ROTATE,) if key_id is not None else (ACKNOWLEDGE,)
        return [_alert(
            "security_compromised",
            CRITICAL,
            provider,
            "Security status COMPROMISED: follow the key loss procedure.",
            actions,
            key_id,
        )]
    return []


def _contact_alerts(record):
    """Return the alert for contact details that need an external update.

    Only the stored status is read; the app never stores contact details
    (section 23.1).
    """
    if record.get("contact_info_verified") == _CONTACT_NEEDS_UPDATE:
        return [_alert(
            "contact_info_unconfirmed",
            INFO,
            "Contact information",
            "The contact details for this key need an external update. "
            "Update them in your external documentation, then close this alert.",
            (ACKNOWLEDGE,),
        )]
    return []
