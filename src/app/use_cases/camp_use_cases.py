"""
Lógica de negocio exclusiva del evento TCS Camp.

Responsabilidades:
  - Consulta de semanas y paquetes disponibles.
  - Cálculo de unit_price por niño según enrollment_type.
  - Validaciones de negocio (stock, duplicados, campos condicionales).
  - Descuento / restauración atómica de stock de semanas.
"""

import logging
from sqlalchemy.orm import Session

from src.domain.entities.camp_week import CampWeek
from src.domain.entities.camp_package import CampPackage
from src.domain.entities.order_camp_enrollment import OrderCampEnrollment
from src.infra.adapters.camp_week_repository import CampWeekRepositorySQL
from src.infra.adapters.camp_package_repository import CampPackageRepositorySQL
from src.infra.adapters.camp_enrollment_repository import CampEnrollmentRepositorySQL
from src.infra.config.settings import get_settings

logger = logging.getLogger("app")


def _get_week_ids_from_package(package: CampPackage) -> list[int]:
    """Parsea el campo week_ids (CSV) de un paquete."""
    if not package.week_ids:
        return []
    return [int(wid.strip()) for wid in package.week_ids.split(",") if wid.strip()]


class CampUseCases:
    def __init__(self, db: Session):
        self.db = db
        self.week_repo = CampWeekRepositorySQL(db)
        self.package_repo = CampPackageRepositorySQL(db)
        self.enrollment_repo = CampEnrollmentRepositorySQL(db)
        self.settings = get_settings()

    # -------------------------------------------------------
    # CONSULTAS PÚBLICAS
    # -------------------------------------------------------

    def get_weeks_by_event(self, event_id: int) -> list[dict]:
        """Retorna semanas activas con stock actual para un evento Camp."""
        weeks = self.week_repo.get_by_event(event_id)
        return [
            {
                "id": w.id,
                "week_number": w.week_number,
                "label": w.label,
                "start_date": w.start_date.isoformat(),
                "end_date": w.end_date.isoformat(),
                "days": w.days,
                "price": w.price,
                "stock": w.stock,
            }
            for w in weeks
        ]

    def get_packages_by_event(self, event_id: int) -> list[dict]:
        """Retorna paquetes activos para un evento Camp."""
        packages = self.package_repo.get_by_event(event_id)
        return [
            {
                "id": p.id,
                "code": p.code,
                "label": p.label,
                "price": p.price,
                "week_ids": _get_week_ids_from_package(p),
            }
            for p in packages
        ]

    # -------------------------------------------------------
    # CREACIÓN DE INSCRIPCIONES (llamado desde OrderUseCases)
    # -------------------------------------------------------

    def resolve_and_validate_children(
        self,
        event_id: int,
        children: list[dict],
    ) -> tuple[int, list[dict]]:
        """
        Valida cada niño, resuelve el unit_price y calcula el total.

        Retorna:
            (total_amount, lista de enrollment dicts listos para persistir)

        Lanza ValueError si alguna validación falla.
        """
        day_price = getattr(self.settings, "CAMP_DAY_PRICE", 200_000)

        resolved = []
        total = 0
        seen_names = set()

        for child in children:
            first = (child.get("child_first_name") or "").strip().upper()
            last = (child.get("child_last_name") or "").strip().upper()
            enrollment_type = child.get("enrollment_type")
            camp_week_id = child.get("camp_week_id")
            camp_package_id = child.get("camp_package_id")
            individual_date = child.get("individual_date")

            # Duplicados dentro de la misma orden
            child_nit = (child.get("child_nit") or "").strip()
            name_key = f"{first}|{last}|{child_nit}|{camp_week_id}|{camp_package_id}|{individual_date}"
            if name_key in seen_names:
                raise ValueError(
                    f"El niño '{first} {last}' aparece duplicado en la misma semana/paquete."
                )
            seen_names.add(name_key)

            if enrollment_type == "WEEK":
                week = self.week_repo.get_by_id(camp_week_id)
                if not week or not week.is_active:
                    raise ValueError(f"La semana {camp_week_id} no está disponible.")
                if week.event_id != event_id:
                    raise ValueError(
                        f"La semana {camp_week_id} no pertenece a este evento."
                    )
                if week.stock < 1:
                    raise ValueError(
                        f"No hay cupos disponibles en '{week.label}'."
                    )
                unit_price = week.price

            elif enrollment_type == "PACKAGE":
                pkg = self.package_repo.get_by_id(camp_package_id)
                if not pkg or not pkg.is_active:
                    raise ValueError(f"El paquete {camp_package_id} no está disponible.")
                if pkg.event_id != event_id:
                    raise ValueError(
                        f"El paquete {camp_package_id} no pertenece a este evento."
                    )
                # Validar stock de cada semana incluida en el paquete
                week_ids = _get_week_ids_from_package(pkg)
                for wid in week_ids:
                    w = self.week_repo.get_by_id(wid)
                    if not w or w.stock < 1:
                        raise ValueError(
                            f"Una semana del paquete '{pkg.label}' no tiene cupos."
                        )
                unit_price = pkg.price

            elif enrollment_type == "DAY":
                # Validar que individual_date caiga en una semana activa del evento
                if individual_date is None:
                    raise ValueError("individual_date requerida para inscripción por día.")
                week = self._find_week_for_date(event_id, individual_date)
                if not week:
                    raise ValueError(
                        f"La fecha {individual_date} no cae en ninguna semana activa del Camp."
                    )
                if week.stock < 1:
                    raise ValueError(
                        f"No hay cupos disponibles para la fecha {individual_date}."
                    )
                unit_price = day_price

            else:
                raise ValueError(f"enrollment_type inválido: {enrollment_type}")

            total += unit_price
            resolved.append({
                **child,
                "unit_price": unit_price,
                "event_id": event_id,
            })

        return total, resolved

    def _find_week_for_date(self, event_id: int, target_date) -> CampWeek | None:
        """Encuentra la semana activa que contiene target_date."""
        weeks = self.week_repo.get_by_event(event_id)
        for w in weeks:
            if w.start_date <= target_date <= w.end_date:
                return w
        return None

    def create_enrollments(self, order_id: str, children: list[dict]):
        """
        Persiste las inscripciones y descuenta stock de forma atómica.
        Debe llamarse dentro de la misma transacción de la orden.
        """
        for child in children:
            enrollment = OrderCampEnrollment(
                order_id=order_id,
                event_id=child["event_id"],
                child_first_name=child["child_first_name"],
                child_last_name=child["child_last_name"],
                child_nit_type=child.get("child_nit_type"),
                child_nit=child.get("child_nit"),
                age_group=child["age_group"],
                enrollment_type=child["enrollment_type"],
                camp_week_id=child.get("camp_week_id"),
                camp_package_id=child.get("camp_package_id"),
                individual_date=child.get("individual_date"),
                unit_price=child["unit_price"],
            )
            self.enrollment_repo.create(enrollment)

            # Descontar stock
            enrollment_type = child["enrollment_type"]
            if enrollment_type == "WEEK":
                self.week_repo.decrease_stock(child["camp_week_id"])
            elif enrollment_type == "PACKAGE":
                pkg = self.package_repo.get_by_id(child["camp_package_id"])
                for wid in _get_week_ids_from_package(pkg):
                    self.week_repo.decrease_stock(wid)
            elif enrollment_type == "DAY":
                # El día suelto descuenta cupo de la semana en que cae
                week = self._find_week_for_date(child["event_id"], child["individual_date"])
                if week:
                    self.week_repo.decrease_stock(week.id)

    def restore_stock_for_order(self, order):
        """
        Restaura cupos al eliminar una orden PENDING.
        Debe llamarse dentro de la misma transacción del delete.
        """
        for enrollment in order.camp_enrollments:
            if enrollment.enrollment_type == "WEEK" and enrollment.camp_week_id:
                self.week_repo.restore_stock(enrollment.camp_week_id)
            elif enrollment.enrollment_type == "PACKAGE" and enrollment.camp_package_id:
                pkg = self.package_repo.get_by_id(enrollment.camp_package_id)
                for wid in _get_week_ids_from_package(pkg):
                    self.week_repo.restore_stock(wid)
            elif enrollment.enrollment_type == "DAY" and enrollment.individual_date:
                week = self._find_week_for_date(
                    enrollment.event_id, enrollment.individual_date
                )
                if week:
                    self.week_repo.restore_stock(week.id)
