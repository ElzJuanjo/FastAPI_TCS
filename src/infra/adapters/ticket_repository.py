from datetime import date, datetime, timedelta

from sqlalchemy import or_, and_
from sqlalchemy.orm import Session

from src.domain.entities.order_ticket import OrderTicket
from src.domain.repositories import TicketRepository
from src.infra.config.settings import get_settings


class TicketRepositorySQL(TicketRepository):
    def __init__(self, db: Session):
        self.db = db

    def create(self, ticket: OrderTicket):
        self.db.add(ticket)
        self.db.flush()
        return ticket

    def get_by_order_id(self, order_id: str):
        return (
            self.db.query(OrderTicket)
            .filter_by(order_id=order_id)
            .first()
        )

    def get_occupied_seats(
        self,
        event_id: int,
        day: date,
        exclude_order_id: str | None = None,
    ) -> list[str]:
        """
        Devuelve los asientos que NO deben poder ser seleccionados por
        otro comprador para un evento y día específicos.
        """
        from src.domain.entities.order import Order

        settings = get_settings()
        # `created_at` en Order se guarda como naive en zona Bogota
        # (ver Order._now_bogota). Mantenemos coherencia: usamos la
        # misma zona y descartamos tzinfo para que SQL Server compare
        # contra una columna DateTime sin zona.
        now_local = datetime.now(settings.TIMEZONE).replace(tzinfo=None)
        ttl_cutoff = now_local - timedelta(
            minutes=settings.SEAT_RESERVATION_TTL_MINUTES
        )

        query = (
            self.db.query(OrderTicket)
            .join(Order, Order.id == OrderTicket.order_id)
            .filter(
                OrderTicket.event_id == event_id,
                OrderTicket.day == day,
                or_(
                    Order.status == "PAID",
                    and_(
                        Order.status == "PENDING",
                        Order.created_at >= ttl_cutoff,
                    ),
                ),
            )
        )

        if exclude_order_id:
            query = query.filter(Order.id != exclude_order_id)

        tickets = query.all()

        occupied: list[str] = []
        for ticket in tickets:
            if ticket.seats:
                occupied.extend(
                    s.strip() for s in ticket.seats.split(",") if s.strip()
                )

        return occupied

    def delete_by_order_id(self, order_id: str):
        self.db.query(OrderTicket).filter_by(order_id=order_id).delete()
        self.db.flush()