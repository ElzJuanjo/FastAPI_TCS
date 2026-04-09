from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from src.infra.config.database import get_db
from src.infra.adapters.wompi_adapter import validate_wompi_event_signature
from src.app.use_cases.payment_use_cases import PaymentUseCases

router = APIRouter(prefix="/api/webhooks", tags=["Webhooks"])


@router.post("/wompi")
async def wompi_webhook(request: Request, db: Session = Depends(get_db)):
    signature = request.headers.get("X-Event-Checksum")
    payload = await request.body()

    if not signature:
        raise HTTPException(status_code=400, detail="Firma ausente")

    if not validate_wompi_event_signature(payload, signature):
        raise HTTPException(status_code=401, detail="Firma inválida")

    event = await request.json()
    transaction = event["data"]["transaction"]

    uc = PaymentUseCases(db)
    try:
        uc.process_wompi_webhook(transaction)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

    return {"status": "ok"}


@router.post("/placetopay")
async def placetopay_webhook(request: Request, db: Session = Depends(get_db)):
    """
    Webhook de notificación de PlaceToPay.
    PlaceToPay envía un POST con { requestId, reference, signature }.
    """
    body = await request.json()
    reference = body.get("reference")

    if not reference:
        raise HTTPException(status_code=400, detail="Reference ausente")

    uc = PaymentUseCases(db)
    try:
        result = uc.check_placetopay_status(reference)
        return result
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
