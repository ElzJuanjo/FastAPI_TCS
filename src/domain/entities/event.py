from sqlalchemy import Column, Integer, String, DateTime, Text, Boolean
from src.infra.config.database import Base


class Event(Base):
    __tablename__ = "events"

    id = Column(Integer, primary_key=True, autoincrement=True)

    title = Column(String(150), nullable=False)
    date = Column(DateTime, nullable=False)
    location = Column(String(200), nullable=True)

    ticket_price = Column(Integer, nullable=False)
    staff_price = Column(Integer, nullable=False)
    combo_price = Column(Integer, nullable=False)

    description = Column(Text, nullable=True)

    stock = Column(Integer, nullable=False)

    is_active = Column(Boolean, default=True, nullable=False)
