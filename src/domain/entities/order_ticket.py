from datetime import datetime, date

from sqlalchemy import Column, Integer, String, DateTime, Date, ForeignKey
from sqlalchemy.orm import relationship

from src.infra.config.database import Base
from src.infra.config.settings import get_settings


def _now_bogota():
    return datetime.now(get_settings().TIMEZONE)


class OrderTicket(Base):
    """
    TABLA - Boletos para eventos de teatro/cine.
    Cada registro representa la selección de asientos de una orden para UN DÍA específico.
    """
    __tablename__ = "order_tickets"

    id = Column(Integer, primary_key=True, autoincrement=True)

    order_id = Column(
        String(36),
        ForeignKey("orders.id", ondelete="CASCADE"),
        nullable=False,
    )

    event_id = Column(
        Integer,
        ForeignKey("events.id", ondelete="NO ACTION"),
        nullable=False,
    )

    day = Column(Date, nullable=False)

    amount = Column(Integer, nullable=False)

    seats = Column(String(500), nullable=False)

    created_at = Column(DateTime, default=_now_bogota)

    # Relations
    order = relationship("Order", back_populates="tickets")
    event = relationship("Event", backref="order_tickets")