from datetime import date
from sqlalchemy.orm import Session
from sqlalchemy import desc

from src.domain.entities.order import Order
from src.domain.entities.order_attendee import OrderAttendee
from src.domain.entities.order_ticket import OrderTicket
from src.domain.entities.event import Event
from src.infra.adapters.order_repository import OrderRepositorySQL
from src.infra.adapters.ticket_repository import TicketRepositorySQL


REQUIRED_BUYER_FIELDS = [
    "nit_type",
    "nit",
    "first_name",
    "last_name_1",
    "email",
    "cell_phone",
    "person_source",
    "event_id",
    "siesa_id",
]


def _get_price_for_person(event: Event, person_source: str) -> int:
    if person_source == "EMPLOYEE":
        return event.staff_price
    return event.ticket_price


def _calculate_total_attendees(event: Event, attendees: list[dict]) -> int:
    """Cálculo legacy para evento de carreras."""
    num = len(attendees)
    if num == 3:
        return event.combo_price
    elif num >= 4:
        return event.staff_price * num
    else:
        total = 0
        for att in attendees:
            total += _get_price_for_person(event, att.get("person_source"))
        return total


def _calculate_total_tickets(event: Event, amount: int, person_source: str) -> int:
    """Cálculo para evento de teatro/cine."""
    price = _get_price_for_person(event, person_source)
    return price * amount


def _validate_buyer(buyer: dict):
    nit = buyer.get("nit")
    person_source = buyer.get("person_source")

    if not nit:
        raise ValueError("Falta el documento del comprador.")
    if not person_source:
        raise ValueError("El comprador debe estar registrado en el sistema.")

    valid_sources = ["EMPLOYEE", "STUDENT", "FAMILY"]
    if person_source not in valid_sources:
        raise ValueError("El comprador debe ser parte de la comunidad.")


def _create_attendees(db: Session, order: Order, attendees: list[dict]):
    """Crea registros de asistentes (evento carreras)."""
    for att_data in attendees:
        attendee = OrderAttendee(
            order_id=order.id,
            event_id=order.event_id,
            nit_type=att_data.get("nit_type", "CC"),
            nit=att_data.get("nit"),
            first_name=att_data.get("first_name"),
            middle_name=att_data.get("middle_name"),
            last_name_1=att_data.get("last_name_1"),
            last_name_2=att_data.get("last_name_2"),
            birth_date=att_data.get("birth_date"),
            email=att_data.get("email"),
            cell_phone=att_data.get("cell_phone"),
            person_source=att_data.get("person_source"),
            is_adult=att_data.get("is_adult", False),
            shirt_size=att_data.get("shirt_size"),
            age_range=att_data.get("age_range"),
            eps=att_data.get("eps"),
            emergency_contact_name=att_data.get("emergency_contact_name"),
            emergency_contact_phone=att_data.get("emergency_contact_phone"),
            medical_info=att_data.get("medical_info"),
        )
        db.add(attendee)


def _create_ticket(db: Session, order: Order, ticket_data: dict):
    """Crea registro de boletos (evento teatro/cine)."""
    ticket = OrderTicket(
        order_id=order.id,
        event_id=order.event_id,
        day=ticket_data["day"],
        amount=ticket_data["amount"],
        seats=ticket_data["seats"],
    )
    db.add(ticket)
    db.flush()
    return ticket


class OrderUseCases:
    def __init__(self, db: Session):
        self.db = db
        self.order_repo = OrderRepositorySQL(db)
        self.ticket_repo = TicketRepositorySQL(db)

    def get_by_id(self, order_id: str):
        return self.order_repo.get_by_id(order_id)

    def get_by_person(self, nit_type: str, nit: str):
        return self.order_repo.get_by_person(nit_type, nit)

    def get_all(self):
        return (
            self.db.query(Order)
            .order_by(desc(Order.created_at))
            .all()
        )

    def delete(self, order_id: str):
        order = self.order_repo.get_by_id(order_id)
        if not order:
            raise ValueError("Orden no encontrada")
        if order.status != "PENDING":
            raise ValueError("Solo se pueden eliminar órdenes en estado pendiente")

        # Restaurar cupos de Camp si aplica
        if order.camp_enrollments:
            from src.app.use_cases.camp_use_cases import CampUseCases
            camp_uc = CampUseCases(self.db)
            camp_uc.restore_stock_for_order(order)

        self.order_repo.delete(order)

    def get_occupied_seats(
        self,
        event_id: int,
        day: date,
        exclude_order_id: str | None = None,
    ) -> list[str]:
        """
        Retorna asientos ocupados para un evento en un día específico.

        Incluye:
          - Órdenes PAID (bloqueo definitivo).
          - Órdenes PENDING dentro de la ventana de reserva temporal
            (SEAT_RESERVATION_TTL_MINUTES).

        Excluye:
          - FAILED / CANCELLED / otros estados finales.
          - PENDING vencidas (TTL expirado) -> se liberan automáticamente.
          - La orden indicada en `exclude_order_id` (útil para updates).
        """
        return self.ticket_repo.get_occupied_seats(
            event_id, day, exclude_order_id=exclude_order_id
        )

    # ===========================================
    # CREAR ORDEN
    # ===========================================
    def create_order(
        self,
        buyer: dict,
        attendees: list[dict] | None = None,
        tickets: dict | None = None,
        camp_children: list[dict] | None = None,
    ) -> Order:
        # Validar campos requeridos del comprador
        for field in REQUIRED_BUYER_FIELDS:
            if not buyer.get(field):
                raise ValueError(f"Campo faltante en comprador: {field}")

        event = self.db.query(Event).get(buyer["event_id"])
        if not event or not event.is_active:
            raise ValueError("Evento no válido")

        _validate_buyer(buyer)

        # Determinar tipo de evento
        is_theater = tickets is not None
        is_race = attendees is not None and len(attendees) > 0
        is_camp = camp_children is not None and len(camp_children) > 0

        if not is_theater and not is_race and not is_camp:
            raise ValueError(
                "Debe proporcionar tickets (teatro), attendees (carreras) "
                "o camp_children (camp)"
            )

        if is_camp:
            # ---- CAMP ----
            from src.app.use_cases.camp_use_cases import CampUseCases
            camp_uc = CampUseCases(self.db)
            total_amount, resolved_children = camp_uc.resolve_and_validate_children(
                event_id=buyer["event_id"],
                children=camp_children,
            )

        elif is_theater:
            # ---- TEATRO/CINE ----
            seats_list = [s.strip() for s in tickets["seats"].split(",") if s.strip()]
            if len(seats_list) != tickets["amount"]:
                raise ValueError(
                    f"La cantidad de asientos ({tickets['amount']}) "
                    f"no coincide con los asientos proporcionados ({len(seats_list)})"
                )

            # Validar que no estén ocupados PARA ESE DÍA
            occupied = self.ticket_repo.get_occupied_seats(
                buyer["event_id"], tickets["day"]
            )
            conflicts = [s for s in seats_list if s in occupied]
            if conflicts:
                raise ValueError(
                    f"Los siguientes asientos ya están ocupados para el día "
                    f"{tickets['day']}: {', '.join(conflicts)}"
                )

            # Validar stock
            if tickets["amount"] > event.stock:
                raise ValueError("No hay suficientes asientos disponibles")

            total_amount = _calculate_total_tickets(
                event, tickets["amount"], buyer["person_source"]
            )

        else:
            # ---- CARRERAS (legacy) ----
            if len(attendees) > 10:
                raise ValueError("Máximo 10 asistentes por orden")
            total_amount = _calculate_total_attendees(event, attendees)

        # Crear orden
        order = Order(
            nit_type=buyer["nit_type"],
            nit=buyer["nit"],
            first_name=buyer["first_name"],
            middle_name=buyer.get("middle_name"),
            last_name_1=buyer["last_name_1"],
            last_name_2=buyer.get("last_name_2"),
            birth_date=buyer.get("birth_date"),
            email=buyer["email"],
            cell_phone=buyer["cell_phone"],
            siesa_id=buyer["siesa_id"],
            person_source=buyer["person_source"],
            family_id=buyer.get("family_id"),
            event_id=buyer["event_id"],
            total_amount=total_amount,
        )

        self.order_repo.create(order)

        if is_camp:
            camp_uc.create_enrollments(order.id, resolved_children)

        elif is_theater:
            _create_ticket(self.db, order, tickets)

            occupied_now = self.ticket_repo.get_occupied_seats(
                buyer["event_id"],
                tickets["day"],
                exclude_order_id=order.id,
            )
            conflicts_now = [s for s in seats_list if s in occupied_now]
            if conflicts_now:
                self.db.rollback()
                raise ValueError(
                    f"Los siguientes asientos fueron tomados por otro "
                    f"usuario mientras completaba su solicitud: "
                    f"{', '.join(conflicts_now)}. Por favor seleccione otros."
                )
        else:
            _create_attendees(self.db, order, attendees)

        self.db.commit()
        return order

    # ===========================================
    # ACTUALIZAR ORDEN
    # ===========================================
    def update_order(
        self,
        order_id: str,
        buyer: dict,
        attendees: list[dict] | None = None,
        tickets: dict | None = None,
        camp_children: list[dict] | None = None,
    ) -> Order:
        order = self.order_repo.get_by_id(order_id)
        if not order:
            raise ValueError("Orden no encontrada")

        for field in REQUIRED_BUYER_FIELDS:
            if not buyer.get(field):
                raise ValueError(f"Campo faltante en comprador: {field}")

        event = self.db.query(Event).get(buyer["event_id"])
        if not event or not event.is_active:
            raise ValueError("Evento no válido")

        _validate_buyer(buyer)

        is_theater = tickets is not None
        is_race = attendees is not None and len(attendees) > 0
        is_camp = camp_children is not None and len(camp_children) > 0

        if not is_theater and not is_race and not is_camp:
            raise ValueError(
                "Debe proporcionar tickets (teatro), attendees (carreras) "
                "o camp_children (camp)"
            )

        if is_camp:
            from src.app.use_cases.camp_use_cases import CampUseCases
            camp_uc = CampUseCases(self.db)
            total_amount, resolved_children = camp_uc.resolve_and_validate_children(
                event_id=buyer["event_id"],
                children=camp_children,
            )

        elif is_theater:
            seats_list = [s.strip() for s in tickets["seats"].split(",") if s.strip()]
            if len(seats_list) != tickets["amount"]:
                raise ValueError(
                    "La cantidad no coincide con los asientos proporcionados"
                )

            occupied = self.ticket_repo.get_occupied_seats(
                buyer["event_id"],
                tickets["day"],
                exclude_order_id=order_id,
            )
            conflicts = [s for s in seats_list if s in occupied]
            if conflicts:
                raise ValueError(
                    f"Asientos ya ocupados para el día {tickets['day']}: "
                    f"{', '.join(conflicts)}"
                )

            total_amount = _calculate_total_tickets(
                event, tickets["amount"], buyer["person_source"]
            )

        else:
            if len(attendees) > 10:
                raise ValueError("Máximo 10 asistentes por orden")
            total_amount = _calculate_total_attendees(event, attendees)

        # Actualizar datos del comprador
        order.nit_type = buyer["nit_type"]
        order.nit = buyer["nit"]
        order.first_name = buyer["first_name"]
        order.middle_name = buyer.get("middle_name")
        order.last_name_1 = buyer["last_name_1"]
        order.last_name_2 = buyer.get("last_name_2")
        order.birth_date = buyer.get("birth_date")
        order.email = buyer["email"]
        order.cell_phone = buyer["cell_phone"]
        order.siesa_id = buyer["siesa_id"]
        order.person_source = buyer["person_source"]
        order.family_id = buyer.get("family_id")
        order.event_id = buyer["event_id"]
        order.total_amount = total_amount

        if is_camp:
            # Restaurar stock anterior y reemplazar inscripciones
            camp_uc.restore_stock_for_order(order)
            from src.infra.adapters.camp_enrollment_repository import CampEnrollmentRepositorySQL
            CampEnrollmentRepositorySQL(self.db).delete_by_order_id(order_id)
            camp_uc.create_enrollments(order.id, resolved_children)

        elif is_theater:
            self.ticket_repo.delete_by_order_id(order_id)
            _create_ticket(self.db, order, tickets)

            occupied_now = self.ticket_repo.get_occupied_seats(
                buyer["event_id"],
                tickets["day"],
                exclude_order_id=order_id,
            )
            conflicts_now = [s for s in seats_list if s in occupied_now]
            if conflicts_now:
                self.db.rollback()
                raise ValueError(
                    f"Los siguientes asientos fueron tomados por otro "
                    f"usuario mientras completaba su solicitud: "
                    f"{', '.join(conflicts_now)}. Por favor seleccione otros."
                )
        else:
            for att in order.attendees:
                self.db.delete(att)
            self.db.flush()
            _create_attendees(self.db, order, attendees)

        self.db.commit()
        return order

    def get_by_event(self, event_id: int):
        return (
            self.db.query(Order)
            .filter(Order.event_id == event_id)
            .order_by(desc(Order.created_at))
            .all()
        )
