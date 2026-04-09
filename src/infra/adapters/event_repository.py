from sqlalchemy.orm import Session
from src.domain.entities.event import Event
from src.domain.repositories import EventRepository


class EventRepositorySQL(EventRepository):
    def __init__(self, db: Session):
        self.db = db

    def get_by_id(self, event_id: int):
        return self.db.query(Event).get(event_id)

    def get_active(self) -> list:
        return self.db.query(Event).filter_by(is_active=True).all()

    def create(self, data: dict):
        event = Event(**data)
        self.db.add(event)
        self.db.commit()
        self.db.refresh(event)
        return event

    def decrease_stock(self, event_id: int, quantity: int):
        event = self.db.query(Event).get(event_id)
        if not event:
            raise ValueError("Evento no encontrado")
        if event.stock < quantity:
            raise ValueError("Stock insuficiente")

        event.stock -= quantity
        self.db.commit()
        return event
