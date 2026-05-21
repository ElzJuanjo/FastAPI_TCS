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
        """
        Descuento atómico de stock usando UPDATE con WHERE stock >= qty.
        Si afecta 0 filas el stock estaba agotado → ValueError.
        No hace commit propio; el commit lo gestiona el llamador.
        """
        from sqlalchemy import text
        result = self.db.execute(
            text(
                "UPDATE events "
                "SET stock = stock - :qty "
                "WHERE id = :event_id AND stock >= :qty"
            ),
            {"qty": quantity, "event_id": event_id},
        )
        if result.rowcount == 0:
            raise ValueError(
                f"Stock insuficiente para el evento {event_id}. "
                "Es posible que los últimos cupos hayan sido tomados."
            )

    def restore_stock(self, event_id: int, quantity: int):
        """
        Devuelve cupos al evento al cancelar o fallar una orden.
        No hace commit propio; el commit lo gestiona el llamador.
        """
        from sqlalchemy import text
        self.db.execute(
            text(
                "UPDATE events "
                "SET stock = stock + :qty "
                "WHERE id = :event_id"
            ),
            {"qty": quantity, "event_id": event_id},
        )
