from sqlalchemy.orm import Session

from src.domain.entities.camp_package import CampPackage
from src.domain.repositories import CampPackageRepository


class CampPackageRepositorySQL(CampPackageRepository):
    def __init__(self, db: Session):
        self.db = db

    def get_by_event(self, event_id: int) -> list[CampPackage]:
        return (
            self.db.query(CampPackage)
            .filter(CampPackage.event_id == event_id, CampPackage.is_active == True)
            .all()
        )

    def get_by_id(self, package_id: int) -> CampPackage | None:
        return self.db.query(CampPackage).get(package_id)

    def get_day_package(self, event_id: int) -> CampPackage | None:
        """Retorna el paquete con code='DAY' activo para el evento."""
        return (
            self.db.query(CampPackage)
            .filter(
                CampPackage.event_id == event_id,
                CampPackage.code == "DAY",
                CampPackage.is_active == True,
            )
            .first()
        )
