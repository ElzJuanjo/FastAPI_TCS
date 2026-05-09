from sqlalchemy import Column, Integer, String, Boolean, ForeignKey
from sqlalchemy.orm import relationship

from src.infra.config.database import Base


class CampPackage(Base):
    __tablename__ = "camp_packages"

    id = Column(Integer, primary_key=True, autoincrement=True)

    event_id = Column(
        Integer,
        ForeignKey("events.id", ondelete="NO ACTION"),
        nullable=False,
    )

    # Código interno del paquete: PKG_S1S2, PKG_S1S3, PKG_3S, DAY
    code = Column(String(20), nullable=False)
    label = Column(String(200), nullable=True)
    price = Column(Integer, nullable=False)

    # IDs de camp_weeks incluidas en este paquete, separados por coma.
    # Ej: "1,2" o "1,3" o "1,2,3"
    # Se parsea en la capa de aplicación.
    week_ids = Column(String(100), nullable=True)

    is_active = Column(Boolean, default=True, nullable=False)

    # =====================
    # Relations
    # =====================
    event = relationship("Event", backref="camp_packages")
