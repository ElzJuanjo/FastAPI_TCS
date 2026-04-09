import hashlib
import base64
import json
import logging
from datetime import datetime

import httpx

from src.infra.config.settings import get_settings

logger = logging.getLogger("placetopay")
settings = get_settings()


def _generate_auth() -> dict:
    """Genera la autenticación requerida por PlaceToPay (WebCheckout)."""
    import secrets

    nonce = secrets.token_hex(16)
    seed = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S+00:00")

    raw = nonce + seed + settings.PLACETOPAY_TRANKEY
    trankey = base64.b64encode(
        hashlib.sha256(raw.encode("utf-8")).digest()
    ).decode("utf-8")

    nonce_b64 = base64.b64encode(nonce.encode("utf-8")).decode("utf-8")

    return {
        "login": settings.PLACETOPAY_LOGIN,
        "tranKey": trankey,
        "nonce": nonce_b64,
        "seed": seed,
    }


def create_session(
    reference: str,
    description: str,
    amount: int,
    currency: str = "COP",
    buyer_name: str = "",
    buyer_email: str = "",
    return_url: str | None = None,
) -> dict:
    """
    Crea una sesión de pago en PlaceToPay.
    Retorna { request_id, process_url, status } o lanza excepción.
    """
    url = f"{settings.PLACETOPAY_URL}/api/session"
    redirect_url = return_url or settings.PLACETOPAY_RETURN_URL

    payload = {
        "auth": _generate_auth(),
        "payment": {
            "reference": reference,
            "description": description,
            "amount": {
                "currency": currency,
                "total": amount,
            },
        },
        "buyer": {
            "name": buyer_name,
            "email": buyer_email,
        },
        "expiration": (
            datetime.utcnow()
            .replace(hour=23, minute=59, second=59)
            .strftime("%Y-%m-%dT%H:%M:%S+00:00")
        ),
        "returnUrl": f"{redirect_url}?ref={reference}",
        "ipAddress": "127.0.0.1",
        "userAgent": "EventsAPI/1.0",
    }

    logger.info(f"PlaceToPay create session | ref={reference}")

    response = httpx.post(url, json=payload, timeout=30)
    data = response.json()

    if data.get("status", {}).get("status") != "OK":
        msg = data.get("status", {}).get("message", "Error desconocido")
        logger.error(f"PlaceToPay session error: {msg}")
        raise Exception(f"PlaceToPay error: {msg}")

    return {
        "request_id": str(data["requestId"]),
        "process_url": data["processUrl"],
        "status": "PENDING",
    }


def query_session(request_id: str) -> dict:
    """
    Consulta el estado de una sesión existente.
    Retorna { status, transaction_id, payment_method, raw }.
    """
    url = f"{settings.PLACETOPAY_URL}/api/session/{request_id}"

    payload = {"auth": _generate_auth()}

    response = httpx.post(url, json=payload, timeout=30)
    data = response.json()

    status_raw = data.get("status", {}).get("status", "PENDING")

    # Mapear estados PlaceToPay → estados internos
    status_map = {
        "APPROVED": "APPROVED",
        "APPROVED_PARTIAL": "APPROVED",
        "REJECTED": "DECLINED",
        "PENDING": "PENDING",
        "FAILED": "ERROR",
    }

    internal_status = status_map.get(status_raw, "PENDING")

    # Extraer datos de transacción si existen
    transactions = data.get("payment", [])
    transaction_id = None
    payment_method_type = None
    extra = {}

    if transactions and isinstance(transactions, list) and len(transactions) > 0:
        tx = transactions[0]
        transaction_id = str(tx.get("internalReference", ""))
        payment_method_type = tx.get("paymentMethodName", "")
        extra = {
            "franchise": tx.get("franchise", ""),
            "last_four": tx.get("lastDigits", ""),
            "external_identifier": tx.get("authorization", ""),
        }

    return {
        "status": internal_status,
        "transaction_id": transaction_id,
        "payment_method": payment_method_type,
        "extra": extra,
        "raw": data,
    }
