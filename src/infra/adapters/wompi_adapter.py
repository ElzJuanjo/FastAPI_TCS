import hashlib
import hmac
import json

from src.infra.config.settings import get_settings


settings = get_settings()


def validate_wompi_event_signature(payload: bytes, signature: str) -> bool:
    if not signature:
        return False

    try:
        event = json.loads(payload)
        internal_checksum = event.get("signature", {}).get("checksum", "")

        if not internal_checksum:
            return False

        return hmac.compare_digest(signature, internal_checksum)
    except (json.JSONDecodeError, KeyError, TypeError):
        return False


def generate_wompi_integrity_signature(
    reference: str,
    amount_in_cents: int,
    currency: str,
) -> str:
    secret = settings.WOMPI_SECRET_INTEGRITY
    raw = f"{reference}{amount_in_cents}{currency}{secret}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()
