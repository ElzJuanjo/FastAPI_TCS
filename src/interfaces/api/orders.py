from datetime import date
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from src.infra.config.database import get_db
from src.interfaces.dependencies import verify_support_key
from src.app.use_cases.order_use_cases import OrderUseCases
from src.app.dto import OrderCreateRequest
from src.infra.config.settings import get_settings

router = APIRouter(prefix="/api/orders", tags=["Orders"])


def _serialize_order(order):
    result = {
        "order_id": order.id,
        "status": order.status,
        "total": order.total_amount,
        "event_id": order.event_id,
        "family_id": order.family_id,
        "buyer": {
            "nit_type": order.nit_type,
            "nit": order.nit,
            "first_name": order.first_name,
            "last_name_1": order.last_name_1,
            "email": order.email,
            "cell_phone": order.cell_phone,
            "siesa_id": order.siesa_id,
            "person_source": order.person_source,
        },
        "created_at": order.created_at.isoformat(),
    }

    # Attendees (carreras)
    if order.attendees:
        result["attendees"] = [
            {
                "id": a.id,
                "nit_type": a.nit_type,
                "nit": a.nit,
                "first_name": a.first_name,
                "last_name_1": a.last_name_1,
                "cell_phone": a.cell_phone,
                "shirt_size": a.shirt_size,
                "age_range": a.age_range,
                "is_adult": a.is_adult,
                "person_source": a.person_source,
            }
            for a in order.attendees
        ]

    # Tickets (teatro/cine)
    if order.tickets:
        result["tickets"] = [
            {
                "id": t.id,
                "day": t.day.isoformat(),
                "amount": t.amount,
                "seats": t.seats,
            }
            for t in order.tickets
        ]

    return result


@router.get("/{order_id}")
def get_order(order_id: str, db: Session = Depends(get_db)):
    uc = OrderUseCases(db)
    order = uc.get_by_id(order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Orden no encontrada")
    return _serialize_order(order)


@router.get("/by-person")
def get_order_by_person(
    nit_type: str = Query(...),
    nit: str = Query(...),
    db: Session = Depends(get_db),
):
    uc = OrderUseCases(db)
    order = uc.get_by_person(nit_type, nit)
    if not order:
        raise HTTPException(status_code=404, detail="Orden no encontrada")
    return _serialize_order(order)


@router.get("")
def get_orders(
    event_id: int | None = Query(None), 
    db: Session = Depends(get_db),
    _: bool = Depends(verify_support_key),
):
    uc = OrderUseCases(db)

    if event_id:
        orders = uc.get_by_event(event_id)
    else:
        orders = uc.get_all()

    return [_serialize_order(o) for o in orders]


@router.get("/seats/occupied/{event_id}")
def get_occupied_seats(
    event_id: int,
    day: date = Query(..., description="Día del evento: YYYY-MM-DD"),
    exclude_order_id: str | None = Query(
        None,
        description=(
            "Opcional. Si se pasa, los asientos de esa orden se excluyen "
            "del listado de ocupados."
        ),
    ),
    db: Session = Depends(get_db),
):
    """
    Retorna los asientos ocupados para un evento en un día específico.

    Un asiento se considera ocupado si pertenece a una orden en estado
    PAID, o en estado PENDING dentro de la ventana de reserva temporal
    (SEAT_RESERVATION_TTL_MINUTES). Las órdenes PENDING vencidas, FAILED
    o CANCELLED se liberan automáticamente.
    """
    uc = OrderUseCases(db)
    seats = uc.get_occupied_seats(event_id, day, exclude_order_id=exclude_order_id)
    return {
        "event_id": event_id,
        "day": day.isoformat(),
        "occupied_seats": seats,
        "ttl_minutes": get_settings().SEAT_RESERVATION_TTL_MINUTES,
    }


@router.post("/new", status_code=201)
def create_new_order(
    data: OrderCreateRequest,
    db: Session = Depends(get_db),
    _: bool = Depends(verify_support_key),
):
    uc = OrderUseCases(db)
    try:
        order = uc.create_order(
            buyer=data.buyer.model_dump(),
            attendees=[a.model_dump() for a in data.attendees] if data.attendees else None,
            tickets=data.tickets.model_dump() if data.tickets else None,
        )
        return {"message": "Orden creada correctamente", "order_id": order.id}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/edit/{order_id}")
def update_existing_order(
    order_id: str,
    data: OrderCreateRequest,
    db: Session = Depends(get_db),
    _: bool = Depends(verify_support_key),
):
    uc = OrderUseCases(db)
    try:
        order = uc.update_order(
            order_id=order_id,
            buyer=data.buyer.model_dump(),
            attendees=[a.model_dump() for a in data.attendees] if data.attendees else None,
            tickets=data.tickets.model_dump() if data.tickets else None,
        )
        return {
            "message": "Orden actualizada correctamente",
            "order": _serialize_order(order),
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception:
        raise HTTPException(status_code=500, detail="Error al actualizar la orden")


@router.delete("/del/{order_id}")
def delete_order(
    order_id: str,
    db: Session = Depends(get_db),
    _: bool = Depends(verify_support_key),
):
    uc = OrderUseCases(db)
    try:
        uc.delete(order_id)
        return {"message": "Orden eliminada correctamente"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))