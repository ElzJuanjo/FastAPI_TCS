from sqlalchemy.orm import Session
from sqlalchemy import text

from src.domain.entities.camp_week import CampWeek
from src.domain.repositories import CampWeekRepository


class CampWeekRepositorySQL(CampWeekRepository):
    def __init__(self, db: Session):
        self.db = db

    def get_by_event(self, event_id: int) -> list[CampWeek]:
        return (
            self.db.query(CampWeek)
            .filter(CampWeek.event_id == event_id, CampWeek.is_active == True)
            .order_by(CampWeek.week_number)
            .all()
        )

    def get_by_id(self, week_id: int) -> CampWeek | None:
        return self.db.query(CampWeek).get(week_id)

    def decrease_stock(self, week_id: int, qty: int = 1):
        """
        Descuento atómico usando UPDATE con WHERE stock >= qty.
        Si afecta 0 filas el cupo estaba agotado → ValueError.
        """
        result = self.db.execute(
            text(
                "UPDATE camp_weeks "
                "SET stock = stock - :qty "
                "WHERE id = :week_id AND stock >= :qty"
            ),
            {"qty": qty, "week_id": week_id},
        )
        if result.rowcount == 0:
            raise ValueError(
                f"Sin cupos disponibles en la semana {week_id}."
            )

    def restore_stock(self, week_id: int, qty: int = 1):
        """Restaura cupos al eliminar una orden PENDING."""
        self.db.execute(
            text(
                "UPDATE camp_weeks "
                "SET stock = stock + :qty "
                "WHERE id = :week_id"
            ),
            {"qty": qty, "week_id": week_id},
        )
