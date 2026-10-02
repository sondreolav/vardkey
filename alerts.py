"""Alert rules derived from a saved health check.

The rules follow the follow-up requirements for the annual health check. The
application only reports these alerts; it never performs the follow-up actions
itself.

The stored status values are intentionally Norwegian (``PROBLEM``,
``IKKJE_VURDERT``, ``SÅRBAR``, ``KOMPROMITTERT``) because they are data values
from the requirement specification. Only the surrounding copy is English.
"""

CRITICAL = "critical"
INFO = "info"

_SEVERITY_ORDER = {CRITICAL: 0, INFO: 1}


def build_alerts(record):
    """Return the active alerts for one saved health check.

    Critical alerts are listed before informational ones; the order within each
    severity follows the checklist order.
    """
    alerts = []
    for key_check in record.get("key_checks") or ():
        alerts.extend(_key_alerts(key_check))
    alerts.extend(_software_alerts(record))
    for tool_check in record.get("tool_checks") or ():
        alerts.extend(_tool_alerts(tool_check))
    for security_check in record.get("ai_security_checks") or ():
        alerts.extend(_security_alerts(security_check))
    alerts.extend(_contact_alerts(record))
    alerts.sort(key=lambda alert: _SEVERITY_ORDER[alert["severity"]])
    return alerts


def _alert(code, severity, source, message):
    return {"code": code, "severity": severity, "source": source, "message": message}


def _key_alerts(key_check):
    """Return the alerts for one key check."""
    source = f"Key {key_check.get('key_number')}: {key_check.get('name')}"
    alerts = []

    if key_check.get("available") == 0:
        alerts.append(_alert(
            "key_unavailable",
            CRITICAL,
            source,
            "This key was not available. Immediate follow-up is required.",
        ))
    if key_check.get("hardware_works") == 0:
        alerts.append(_alert(
            "hardware_failure",
            CRITICAL,
            source,
            "The hardware does not work. Test the seed backup on another compatible device.",
        ))
    if key_check.get("seed_backup_status") == "PROBLEM":
        alerts.append(_alert(
            "seed_backup_problem",
            CRITICAL,
            source,
            "The seed backup is missing or damaged. Activate PROTOCOL 3: key loss.",
        ))
    if key_check.get("address_verified") == 0 or key_check.get("address_path_verified") == 0:
        alerts.append(_alert(
            "address_verification_failed",
            CRITICAL,
            source,
            "Address verification failed. Check the address against BSMS and test it again.",
        ))
    return alerts


def _software_alerts(record):
    """Return the alert for software that no longer supports the hardware."""
    if record.get("software_compatibility_status") == "PROBLEM":
        return [_alert(
            "software_incompatible",
            CRITICAL,
            "Software compatibility",
            "The software no longer supports the hardware. Consider alternative software.",
        )]
    return []


def _tool_alerts(tool_check):
    """Return the informational alerts for reported BIP327 or SLIP39 support."""
    product = tool_check.get("product")
    alerts = []

    if tool_check.get("bip327_status") == "OK":
        alerts.append(_alert(
            "bip327_available",
            INFO,
            f"{product} (BIP327)",
            "BIP327 support is reported as available. A future BIP327 upgrade can be considered.",
        ))
    if tool_check.get("slip39_status") == "OK":
        alerts.append(_alert(
            "slip39_available",
            INFO,
            f"{product} (SLIP39)",
            "SLIP39 support is reported as available. A future SLIP39 activation can be considered.",
        ))
    return alerts


def _security_alerts(security_check):
    """Return the alerts for one external security status."""
    provider = security_check.get("provider")
    status = security_check.get("status")

    if status == "SÅRBAR":
        return [_alert(
            "security_vulnerable",
            CRITICAL,
            provider,
            "Security status SÅRBAR: the firmware or security problem must be followed up.",
        )]
    if status == "KOMPROMITTERT":
        return [_alert(
            "security_compromised",
            CRITICAL,
            provider,
            "Security status KOMPROMITTERT: follow the key loss procedure.",
        )]
    return []


def _contact_alerts(record):
    """Return the alert for contact information that is not confirmed."""
    if record.get("contact_info_verified") == 0:
        return [_alert(
            "contact_info_unconfirmed",
            INFO,
            "Contact information",
            "Contact information is not confirmed. Update it in your external documentation.",
        )]
    return []
