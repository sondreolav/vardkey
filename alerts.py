"""Alert rules derived from a saved health check.

The rules follow the follow-up requirements for the annual health check. The
application only reports these alerts; it never performs the follow-up actions
itself.

One saved check covers one key. A key that was not available produces a single
critical alert, because the remaining checks for that key could not be
performed. For the cloud key the cloud results are derived from availability
(section 20), so that one alert mentions both facts.
"""

CRITICAL = "critical"
INFO = "info"

_SEVERITY_ORDER = {CRITICAL: 0, INFO: 1}

_KEY_UNAVAILABLE_MESSAGE = (
    "This key was not available. Replace the key before continuing; "
    "the remaining checks for this key cannot be recorded."
)
_CLOUD_KEY_UNAVAILABLE_MESSAGE = (
    "This key was not available and the cloud provider is recorded as not operating. "
    "Check the provider status and replace the key before continuing; "
    "the remaining checks for this key cannot be recorded."
)


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
    if key_check.get("available") == 0:
        # The remaining checks for this key could not be performed.
        message = (
            _CLOUD_KEY_UNAVAILABLE_MESSAGE
            if key_check.get("type") == "cloud"
            else _KEY_UNAVAILABLE_MESSAGE
        )
        return [_alert("key_unavailable", CRITICAL, source, message)]

    alerts = []
    if key_check.get("hardware_works") == 0:
        alerts.append(_alert(
            "hardware_failure",
            CRITICAL,
            source,
            "The hardware does not work. Test the seed backup on another compatible device.",
        ))
    if key_check.get("seed_backup_verified") == "PROBLEM":
        alerts.append(_alert(
            "seed_backup_problem",
            CRITICAL,
            source,
            "The seed backup is missing or damaged. Activate PROTOCOL 3: key loss.",
        ))
    if (key_check.get("cloud_health_status") == "PROBLEM"
            or key_check.get("cloud_provider_operational") == 0):
        alerts.append(_alert(
            "cloud_provider_problem",
            CRITICAL,
            source,
            "The cloud provider is not operating normally. "
            "Check the provider status before continuing.",
        ))
    if key_check.get("address_path_verified") == "PROBLEM":
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

    if status == "VULNERABLE":
        return [_alert(
            "security_vulnerable",
            CRITICAL,
            provider,
            "Security status VULNERABLE: the firmware or security problem must be followed up.",
        )]
    if status == "COMPROMISED":
        return [_alert(
            "security_compromised",
            CRITICAL,
            provider,
            "Security status COMPROMISED: follow the key loss procedure.",
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
