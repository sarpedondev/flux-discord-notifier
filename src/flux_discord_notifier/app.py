import hashlib
import hmac
import json
import logging
from contextlib import asynccontextmanager

import httpx
from fastapi import FastAPI, Header, HTTPException, Request, Response, status
from pydantic import ValidationError

from .config import Settings
from .dedup import DuplicateCache
from .formatting import classify, discord_payload, event_key
from .models import FluxEvent

logger = logging.getLogger("flux_discord_notifier")
logging.getLogger("httpx").setLevel(logging.WARNING)


def verify_signature(signature: str | None, payload: bytes, token: bytes) -> bool:
    if not signature:
        return False
    algorithm, separator, supplied = signature.partition("=")
    if separator != "=" or algorithm.casefold() != "sha256" or len(supplied) != 64:
        return False
    try:
        bytes.fromhex(supplied)
    except ValueError:
        return False
    expected = hmac.new(token, payload, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, supplied.casefold())


def create_app(
    settings: Settings | None = None,
    transport: httpx.AsyncBaseTransport | None = None,
) -> FastAPI:
    resolved_settings = settings

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        app.state.settings = resolved_settings or Settings.from_env()
        app.state.duplicates = DuplicateCache(
            app.state.settings.dedup_ttl_seconds,
            app.state.settings.dedup_max_entries,
        )
        async with httpx.AsyncClient(
            timeout=app.state.settings.discord_timeout_seconds,
            transport=transport,
        ) as client:
            app.state.discord = client
            yield

    app = FastAPI(
        title="Flux Discord Notifier",
        version="0.1.0",
        docs_url=None,
        redoc_url=None,
        lifespan=lifespan,
    )

    @app.get("/healthz", include_in_schema=False)
    async def healthz() -> dict[str, str]:
        return {"status": "ok"}

    @app.post("/webhooks/flux", status_code=status.HTTP_204_NO_CONTENT)
    async def flux_webhook(
        request: Request,
        x_signature: str | None = Header(default=None, alias="X-Signature"),
    ) -> Response:
        content_length = request.headers.get("content-length")
        if content_length:
            try:
                if int(content_length) > request.app.state.settings.max_payload_bytes:
                    raise HTTPException(status_code=413, detail="payload too large")
            except ValueError as exc:
                raise HTTPException(status_code=400, detail="invalid content length") from exc

        chunks = bytearray()
        async for chunk in request.stream():
            chunks.extend(chunk)
            if len(chunks) > request.app.state.settings.max_payload_bytes:
                raise HTTPException(status_code=413, detail="payload too large")
        body = bytes(chunks)
        if not verify_signature(x_signature, body, request.app.state.settings.hmac_token):
            logger.warning("rejected Flux webhook with invalid signature")
            raise HTTPException(status_code=401, detail="invalid signature")

        try:
            event = FluxEvent.model_validate(json.loads(body))
        except (json.JSONDecodeError, UnicodeDecodeError, ValidationError):
            logger.warning("rejected malformed Flux event")
            raise HTTPException(status_code=422, detail="invalid Flux event") from None

        style = classify(event)
        if style is None:
            logger.info(
                "ignored Flux event kind=%s reason=%s",
                event.involved_object.kind,
                event.reason,
            )
            return Response(status_code=204)

        key = event_key(event, style, request.app.state.settings.cluster_name)
        if not await request.app.state.duplicates.reserve(key):
            logger.info(
                "suppressed duplicate Flux event kind=%s name=%s",
                event.involved_object.kind,
                event.involved_object.name,
            )
            return Response(status_code=204)

        payload = discord_payload(event, style, request.app.state.settings.cluster_name)
        try:
            response = await request.app.state.discord.post(
                request.app.state.settings.discord_webhook_url,
                json=payload,
            )
            response.raise_for_status()
        except httpx.HTTPError:
            await request.app.state.duplicates.release(key)
            logger.error(
                "Discord delivery failed kind=%s name=%s",
                event.involved_object.kind,
                event.involved_object.name,
            )
            raise HTTPException(status_code=502, detail="Discord delivery failed") from None

        logger.info(
            "sent Discord notification kind=%s name=%s state=%s",
            event.involved_object.kind,
            event.involved_object.name,
            style.title,
        )
        return Response(status_code=204)

    return app


app = create_app()
