from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from src.infra.config.database import get_db
from src.interfaces.dependencies import verify_support_key
from src.app.use_cases.payment_use_cases import PaymentUseCases
from src.app.dto import PaymentInitRequest

router = APIRouter(prefix="/api/payments", tags=["Payments"])


@router.post("/init/{order_id}")
def init_payment(
    order_id: str,
    body: PaymentInitRequest = PaymentInitRequest(),
    db: Session = Depends(get_db),
    _: bool = Depends(verify_support_key),
):
    uc = PaymentUseCases(db)
    try:
        result = uc.init_payment(order_id, gateway=body.gateway)
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/approved")
def get_approved_payments(db: Session = Depends(get_db)):
    uc = PaymentUseCases(db)
    payments = uc.get_approved()
    return [
        {
            "payment_id": p.id,
            "order_id": p.order_id,
            "gateway": p.gateway,
            "wompi_transaction_id": p.wompi_transaction_id,
            "placetopay_request_id": p.placetopay_request_id,
            "amount": p.amount,
            "currency": p.currency,
            "payment_method": p.payment_method,
            "created_at": p.created_at.isoformat(),
        }
        for p in payments
    ]


@router.post("/placetopay/check/{order_id}")
def check_placetopay(
    order_id: str,
    db: Session = Depends(get_db),
):
    """
    Endpoint para consultar/actualizar el estado de un pago PlaceToPay.
    El frontend puede llamar esto cuando el usuario retorna de PlaceToPay.
    """
    uc = PaymentUseCases(db)
    try:
        result = uc.check_placetopay_status(order_id)
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
