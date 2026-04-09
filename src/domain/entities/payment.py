from datetime import datetime

from sqlalchemy import Column, Integer, String, DateTime, Text, JSON, ForeignKey
from sqlalchemy.orm import relationship

from src.infra.config.database import Base
from src.infra.config.settings import get_settings


def _now_bogota():
    return datetime.now(get_settings().TIMEZONE)


class Payment(Base):
    __tablename__ = "payments"

    id = Column(Integer, primary_key=True)

    order_id = Column(
        String(36),
        ForeignKey("orders.id", ondelete="CASCADE"),
        nullable=False,
    )

    # =====================
    # EXISTENTE - Wompi (no tocar)
    # =====================
    wompi_transaction_id = Column(String(100), nullable=True)

    status = Column(String(30), nullable=False, default="PENDING")
    amount = Column(Integer, nullable=False)
    currency = Column(String(10), default="COP")

    payment_method = Column(String(50), nullable=True)

    created_at = Column(DateTime, default=_now_bogota)

    siesa_invoice_number = Column(String(50), nullable=True)
    siesa_receipt_number = Column(String(50), nullable=True)
    siesa_error = Column(Text, nullable=True)

    siesa_response = Column(JSON, nullable=True)
    raw_response = Column(JSON, nullable=True)

    # =====================
    # NUEVO - PlaceToPay
    # =====================
    placetopay_request_id = Column(String(100), nullable=True)
    placetopay_session_url = Column(String(500), nullable=True)

    # Gateway: "WOMPI" | "PLACETOPAY"
    gateway = Column(String(20), nullable=True, default="WOMPI")

    # =====================
    # Relations
    # =====================
    order = relationship("Order", back_populates="payments")
