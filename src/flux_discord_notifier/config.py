import os
from dataclasses import dataclass
from pathlib import Path


def _read_secret(path: str, label: str) -> str:
    try:
        value = Path(path).read_text(encoding="utf-8").rstrip("\r\n")
    except OSError as exc:
        raise RuntimeError(f"could not read {label} secret file") from exc
    if not value:
        raise RuntimeError(f"{label} secret file is empty")
    return value


@dataclass(frozen=True, slots=True)
class Settings:
    discord_webhook_url: str
    hmac_token: bytes
    cluster_name: str = "unknown"
    dedup_ttl_seconds: int = 300
    dedup_max_entries: int = 10_000
    max_payload_bytes: int = 256 * 1024
    discord_timeout_seconds: float = 10.0

    @classmethod
    def from_env(cls) -> "Settings":
        discord_path = os.getenv(
            "DISCORD_WEBHOOK_URL_FILE", "/run/secrets/discord-webhook-url"
        )
        hmac_path = os.getenv("FLUX_HMAC_TOKEN_FILE", "/run/secrets/flux-hmac-token")
        return cls(
            discord_webhook_url=_read_secret(discord_path, "Discord webhook URL"),
            hmac_token=_read_secret(hmac_path, "Flux HMAC token").encode("utf-8"),
            cluster_name=os.getenv("CLUSTER_NAME", "unknown"),
            dedup_ttl_seconds=int(os.getenv("DEDUP_TTL_SECONDS", "300")),
            dedup_max_entries=int(os.getenv("DEDUP_MAX_ENTRIES", "10000")),
            max_payload_bytes=int(os.getenv("MAX_PAYLOAD_BYTES", str(256 * 1024))),
            discord_timeout_seconds=float(os.getenv("DISCORD_TIMEOUT_SECONDS", "10")),
        )

