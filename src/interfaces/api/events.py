from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from src.infra.config.database import get_db
from src.interfaces.dependencies import verify_support_key
from src.app.use_cases.event_use_cases import EventUseCases
from src.app.dto import EventCreate

router = APIRouter(prefix="/api/events", tags=["Events"])


def _serialize_event(e):
    return {
        "id": e.id,
        "title": e.title,
        "date": e.date.isoformat(),
        "location": e.location,
        "ticket_price": e.ticket_price,
        "staff_price": e.staff_price,
        "combo_price": e.combo_price,
        "description": e.description,
        "stock": e.stock,
    }


@router.get("")
def list_events(db: Session = Depends(get_db)):
    uc = EventUseCases(db)
    events = uc.list_active()
    return [_serialize_event(e) for e in events]


@router.get("/{event_id}")
def get_event(event_id: int, db: Session = Depends(get_db)):
    uc = EventUseCases(db)
    event = uc.get_by_id(event_id)

    if not event or not event.is_active:
        raise HTTPException(status_code=404, detail="Evento no encontrado")

    return _serialize_event(event)


@router.post("/new", status_code=201)
def create_event(
    data: EventCreate,
    db: Session = Depends(get_db),
    _: bool = Depends(verify_support_key),
):
    uc = EventUseCases(db)
    try:
        event = uc.create(data.model_dump())
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    return {"id": event.id, "message": "Evento creado correctamente"}
