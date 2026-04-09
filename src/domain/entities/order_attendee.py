from datetime import datetime

from sqlalchemy import Column, Integer, String, Boolean, DateTime, Date, ForeignKey
from sqlalchemy.orm import relationship

from src.infra.config.database import Base
from src.infra.config.settings import get_settings


def _now_bogota():
    return datetime.now(get_settings().TIMEZONE)


class OrderAttendee(Base):
    """
    Tabla EXISTENTE en producción - NO modificar columnas.
    Se usa en el evento de carreras. Para el evento de teatro/cine
    no se crean registros aquí, se usa OrderTicket en su lugar.
    """
    __tablename__ = "order_attendees"

    id = Column(Integer, primary_key=True, autoincrement=True)

    order_id = Column(
        String(36),
        ForeignKey("orders.id", ondelete="CASCADE"),
        nullable=False,
    )

    # Attendee personal data
    nit_type = Column(String(10), nullable=False)
    nit = Column(String(20), nullable=False)

    first_name = Column(String(80), nullable=False)
    middle_name = Column(String(80), nullable=True)
    last_name_1 = Column(String(80), nullable=False)
    last_name_2 = Column(String(80), nullable=True)

    birth_date = Column(Date, nullable=True)

    email = Column(String(120), nullable=True)
    cell_phone = Column(String(20), nullable=False)

    # Institutional source
    person_source = Column(
        String(20),
        nullable=False,
        comment="EMPLOYEE | STUDENT | FAMILY",
    )

    event_id = Column(
        Integer,
        ForeignKey("events.id", ondelete="NO ACTION"),
        nullable=False,
    )

    # Extra (carreras)
    is_adult = Column(Boolean, nullable=False, default=False)
    shirt_size = Column(String(10), nullable=False, comment="8|12|14|16|XS|S|M|L|XL")
    age_range = Column(String(20), nullable=False, comment="5-10|11-17|18-25|...")

    created_at = Column(DateTime, default=_now_bogota)

    # Medical data
    eps = Column(String(80), nullable=True)
    emergency_contact_name = Column(String(120), nullable=True)
    emergency_contact_phone = Column(String(20), nullable=True)
    medical_info = Column(String(500), nullable=True)

    # Relations
    order = relationship("Order", back_populates="attendees")
