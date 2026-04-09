from sqlalchemy.orm import Session
from src.infra.adapters.event_repository import EventRepositorySQL


class EventUseCases:
    def __init__(self, db: Session):
        self.repo = EventRepositorySQL(db)

    def list_active(self):
        return self.repo.get_active()

    def get_by_id(self, event_id: int):
        return self.repo.get_by_id(event_id)

    def create(self, data: dict):
        required = ["title", "date", "ticket_price", "staff_price", "combo_price", "stock"]
        for field in required:
            if field not in data or data[field] is None:
                raise ValueError(f"Campo faltante: {field}")
        return self.repo.create(data)

    def decrease_stock(self, event_id: int, quantity: int):
        return self.repo.decrease_stock(event_id, quantity)
