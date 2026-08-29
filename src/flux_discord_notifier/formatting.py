import hashlib
import json
import re
from dataclasses import dataclass
from typing import Any

from .models import FluxEvent

GREEN = 0x2ECC71
RED = 0xE74C3C
BLUE = 0x3498DB
PURPLE = 0x9B59B6


@dataclass(frozen=True, slots=True)
class EventStyle:
    title: str
    color: int


def classify(event: FluxEvent) -> EventStyle | None:
    if event.severity.casefold() == "error":
        return EventStyle("Deployment failed", RED)

    kind = event.involved_object.kind.casefold()
    if kind == "imagepolicy":
        return EventStyle("New image detected", BLUE)
    if kind == "imageupdateautomation" and _is_success(event):
        return EventStyle("Deployment queued", PURPLE)
    if kind == "kustomization" and _is_success(event):
        return EventStyle("Deployment completed", GREEN)
    return None


def _is_success(event: FluxEvent) -> bool:
    text = f"{event.reason} {event.message}".casefold()
    return any(word in text for word in ("succeed", "completed", "finished", "committed", "pushed"))


def _metadata_value(metadata: dict[str, Any], *names: str) -> str | None:
    folded = {key.casefold(): value for key, value in metadata.items()}
    for name in names:
        value = folded.get(name.casefold())
        if value not in (None, ""):
            return str(value)
    return None


def application_name(event: FluxEvent) -> str:
    return _metadata_value(event.metadata, "application", "app", "app.kubernetes.io/name") or event.involved_object.name


def cluster_name(event: FluxEvent, default: str) -> str:
    return _metadata_value(event.metadata, "cluster", "cluster_name", "environment") or default


def revision(event: FluxEvent) -> str:
    explicit = _metadata_value(event.metadata, "revision")
    if explicit:
        return explicit
    for key, value in event.metadata.items():
        if key.casefold().endswith("/revision") and value not in (None, ""):
            return str(value)
    match = re.search(r"(?:revision|updated from|updated to)\s+['\"]?([^\s,'\"]+)", event.message, re.IGNORECASE)
    return match.group(1) if match else "unknown"


def concise_message(message: str, limit: int = 900) -> str:
    compact = " ".join(message.split())
    return compact if len(compact) <= limit else f"{compact[: limit - 1]}…"


def field_value(value: str, limit: int = 500) -> str:
    compact = " ".join(value.split()) or "unknown"
    return compact if len(compact) <= limit else f"{compact[: limit - 1]}…"


def discord_payload(event: FluxEvent, style: EventStyle, default_cluster: str) -> dict[str, Any]:
    return {
        "username": "Flux",
        "avatar_url": "https://fluxcd.io/img/flux-icon@2x.png",
        "allowed_mentions": {"parse": []},
        "embeds": [
            {
                "title": style.title,
                "description": concise_message(event.message),
                "color": style.color,
                "fields": [
                    {"name": "Application", "value": field_value(application_name(event)), "inline": True},
                    {"name": "Cluster", "value": field_value(cluster_name(event, default_cluster)), "inline": True},
                    {"name": "Revision", "value": field_value(revision(event)), "inline": False},
                ],
                "timestamp": event.timestamp.isoformat().replace("+00:00", "Z"),
                "footer": {"text": f"Flux · {event.involved_object.kind}"},
            }
        ],
    }


def event_key(event: FluxEvent, style: EventStyle, default_cluster: str) -> str:
    semantic = {
        "title": style.title,
        "object": event.involved_object.model_dump(mode="json"),
        "severity": event.severity,
        "reason": event.reason,
        "message": event.message,
        "metadata": event.metadata,
        "timestamp": event.timestamp.isoformat(),
        "cluster": cluster_name(event, default_cluster),
    }
    encoded = json.dumps(semantic, sort_keys=True, separators=(",", ":"), default=str).encode()
    return hashlib.sha256(encoded).hexdigest()
