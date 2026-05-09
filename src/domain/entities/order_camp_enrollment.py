from datetime import datetime

from sqlalchemy import Column, Integer, String, Date, DateTime, ForeignKey
from sqlalchemy.orm import relationship

from src.infra.config.database import Base


class OrderCampEnrollment(Base):
    __tablename__ = "order_camp_enrollments"

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

    child_first_name = Column(String(80), nullable=False)
    child_last_name = Column(String(80), nullable=False)
    child_nit_type = Column(String(10), nullable=True)
    child_nit = Column(String(20), nullable=True)

    # Valor libre definido por el evento (ej: K4_1ST, 2ND_3RD, 4TH_5TH)
    age_group = Column(String(30), nullable=False)

    # WEEK | PACKAGE | DAY
    enrollment_type = Column(String(20), nullable=False)

    camp_week_id = Column(
        Integer,
        ForeignKey("camp_weeks.id", ondelete="NO ACTION"),
        nullable=True,
    )

    camp_package_id = Column(
        Integer,
        ForeignKey("camp_packages.id", ondelete="NO ACTION"),
        nullable=True,
    )

    # Solo para enrollment_type = DAY
    individual_date = Column(Date, nullable=True)

    # Precio al momento de crear la orden (trazabilidad histórica)
    unit_price = Column(Integer, nullable=False)

    created_at = Column(DateTime, default=datetime.utcnow)

    # =====================
    # Relations
    # =====================
    order = relationship("Order", back_populates="camp_enrollments")
    camp_week = relationship("CampWeek")
    camp_package = relationship("CampPackage")
