import re
from datetime import date, datetime, time
from decimal import Decimal
from uuid import UUID

from django.db.models.fields.files import FieldFile
from django.utils import timezone

from . import conf

MASKED = "***"


def serialize_value(value):
    """`value` as a JSON-safe primitive (dates as ISO text, decimals as text, files as their name)."""
    if value is None or isinstance(value, (bool, int, float, str)):
        return value
    if isinstance(value, FieldFile):
        return value.name or None
    if isinstance(value, datetime):
        return (timezone.localtime(value) if timezone.is_aware(value) else value).isoformat()
    if isinstance(value, (date, time)):
        return value.isoformat()
    if isinstance(value, (Decimal, UUID)):
        return str(value)
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="ignore")
    if hasattr(value, "_meta"):
        return value.pk
    if isinstance(value, dict):
        return {str(k): serialize_value(v) for k, v in value.items()}
    if isinstance(value, (list, tuple, set, frozenset)):
        return [serialize_value(item) for item in value]
    return str(value)


def snapshot(instance):
    """{field: value} of the record's own columns (links as their id), secrets masked."""
    masked = conf.mask_fields()
    data = {}
    for field in instance._meta.concrete_fields:
        name = field.attname
        if name.lower() in masked or field.name.lower() in masked:
            data[name] = MASKED
            continue
        try:
            data[name] = serialize_value(field.value_from_object(instance))
        except Exception:  # an odd field must not stop the log
            data[name] = None
    return data


def secret_values(instance):
    """{field: real value} of the masked fields, kept in memory only, to notice a secret being changed."""
    masked = conf.mask_fields()
    return {
        field.attname: field.value_from_object(instance)
        for field in instance._meta.concrete_fields
        if field.attname.lower() in masked or field.name.lower() in masked
    }


def auto_fields(model):
    """Columns the database fills in on every save (auto_now): their change is not a real change."""
    return {f.attname for f in model._meta.concrete_fields if getattr(f, "auto_now", False)}


def model_label(model):
    return f"{model._meta.app_label}.{model.__name__}"


def _version(pattern, text):
    found = re.search(pattern, text)
    return found.group(1).replace("_", ".") if found else ""


def device(user_agent):
    """(operating system, browser) read from a User-Agent string, e.g. ("Windows 10", "Chrome").

    A plain best guess with no extra package; anything unknown comes back as "".
    """
    ua = user_agent or ""
    if not ua:
        return "", ""

    if "Windows NT" in ua:
        # Windows 11 still reports "NT 10.0"; the browser does not tell them apart.
        nt = _version(r"Windows NT ([\d.]+)", ua)
        os_name = {"10.0": "Windows 10/11", "6.3": "Windows 8.1", "6.2": "Windows 8", "6.1": "Windows 7"}.get(nt, "Windows")
    elif "Android" in ua:
        os_name = f"Android {_version(r'Android ([\d.]+)', ua)}".strip()
    elif re.search(r"iPhone|iPad|iPod", ua):
        os_name = f"iOS {_version(r'OS ([\d_]+) like Mac OS X', ua)}".strip()
    elif "Mac OS X" in ua or "Macintosh" in ua:
        os_name = "macOS"
    elif "CrOS" in ua:
        os_name = "ChromeOS"
    elif "Linux" in ua:
        os_name = "Linux"
    else:
        os_name = ""

    # Order matters: Edge, Opera and Samsung also say "Chrome", and Chrome also says "Safari".
    for name, pattern in (
        ("Edge", r"Edg(?:e|A|iOS)?/"),
        ("Opera", r"OPR/|Opera"),
        ("Samsung Internet", r"SamsungBrowser/"),
        ("Firefox", r"Firefox/|FxiOS/"),
        ("Chrome", r"Chrome/|CriOS/"),
        ("Safari", r"Safari/"),
        ("Postman", r"PostmanRuntime/"),
        ("curl", r"^curl/"),
    ):
        if re.search(pattern, ua):
            return os_name, name
    return os_name, ""
