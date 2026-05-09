from sqlalchemy import Column, Integer, String, Date, Boolean, ForeignKey
from sqlalchemy.orm import relationship

from src.infra.config.database import Base


class CampWeek(Base):
    __tablename__ = "camp_weeks"

    id = Column(Integer, primary_key=True, autoincrement=True)

    event_id = Column(
        Integer,
        ForeignKey("events.id", ondelete="NO ACTION"),
        nullable=False,
    )

    week_number = Column(Integer, nullable=False)
    label = Column(String(100), nullable=True)
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=False)
    days = Column(Integer, nullable=False)
    price = Column(Integer, nullable=False)
    stock = Column(Integer, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)

    # =====================
    # Relations
    # =====================
    event = relationship("Event", backref="camp_weeks")
