import uuid
from datetime import datetime

from sqlalchemy import Column, String, Integer, DateTime, Date, ForeignKey
from sqlalchemy.orm import relationship

from src.infra.config.database import Base
from src.infra.config.settings import get_settings


def _now_bogota():
    return datetime.now(get_settings().TIMEZONE)


class Order(Base):
    __tablename__ = "orders"

    id = Column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
    )

    # =====================
    # Buyer personal data
    # =====================
    nit_type = Column(String(10), nullable=False)
    nit = Column(String(20), nullable=False)

    first_name = Column(String(80), nullable=False)
    middle_name = Column(String(80), nullable=True)
    last_name_1 = Column(String(80), nullable=False)
    last_name_2 = Column(String(80), nullable=True)

    birth_date = Column(Date, nullable=True)

    email = Column(String(120), nullable=False)
    cell_phone = Column(String(20), nullable=False)

    siesa_id = Column(String(20), nullable=False)

    # =====================
    # Institutional source
    # =====================
    person_source = Column(
        String(20),
        nullable=False,
        comment="EMPLOYEE | STUDENT | FAMILY",
    )

    # =====================
    # NEW: family_id
    # Se agrega como columna nueva, nullable para no romper registros existentes
    # =====================
    family_id = Column(String(50), nullable=True)

    event_id = Column(
        Integer,
        ForeignKey("events.id", ondelete="NO ACTION"),
        nullable=False,
    )

    # =====================
    # Order data
    # =====================
    status = Column(String(30), nullable=False, default="PENDING")

    total_amount = Column(Integer, nullable=False)

    created_at = Column(DateTime, default=_now_bogota)

    # =====================
    # Relations
    # =====================
    payments = relationship(
        "Payment",
        back_populates="order",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

    attendees = relationship(
        "OrderAttendee",
        back_populates="order",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

    tickets = relationship(
        "OrderTicket",
        back_populates="order",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

    event = relationship("Event", backref="orders")
