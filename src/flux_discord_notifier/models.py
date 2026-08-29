from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator


class InvolvedObject(BaseModel):
    model_config = ConfigDict(extra="ignore")

    api_version: str | None = Field(default=None, alias="apiVersion")
    kind: str
    name: str
    namespace: str = "default"
    uid: str | None = None


class FluxEvent(BaseModel):
    model_config = ConfigDict(extra="ignore")

    involved_object: InvolvedObject = Field(alias="involvedObject")
    metadata: dict[str, Any] = Field(default_factory=dict)
    severity: str = "info"
    reason: str = ""
    message: str
    reporting_controller: str | None = Field(default=None, alias="reportingController")
    reporting_instance: str | None = Field(default=None, alias="reportingInstance")
    timestamp: datetime

    @field_validator("timestamp")
    @classmethod
    def require_timezone(cls, value: datetime) -> datetime:
        if value.tzinfo is None:
            raise ValueError("timestamp must include a timezone")
        return value.astimezone(timezone.utc)

