from abc import ABC, abstractmethod
from datetime import date


class EventRepository(ABC):
    @abstractmethod
    def get_by_id(self, event_id: int):
        ...

    @abstractmethod
    def get_active(self) -> list:
        ...

    @abstractmethod
    def create(self, data: dict):
        ...

    @abstractmethod
    def decrease_stock(self, event_id: int, quantity: int):
        ...


class OrderRepository(ABC):
    @abstractmethod
    def get_by_id(self, order_id: str):
        ...

    @abstractmethod
    def get_by_person(self, nit_type: str, nit: str):
        ...

    @abstractmethod
    def get_all(self) -> list:
        ...

    @abstractmethod
    def create(self, order):
        ...

    @abstractmethod
    def update(self, order):
        ...

    @abstractmethod
    def delete(self, order):
        ...


class PaymentRepository(ABC):
    @abstractmethod
    def get_by_order_id(self, order_id: str):
        ...

    @abstractmethod
    def get_approved(self) -> list:
        ...

    @abstractmethod
    def create(self, payment):
        ...

    @abstractmethod
    def update(self, payment):
        ...

    @abstractmethod
    def delete(self, payment):
        ...


class TicketRepository(ABC):
    @abstractmethod
    def create(self, ticket):
        ...

    @abstractmethod
    def get_by_order_id(self, order_id: str):
        ...

    @abstractmethod
    def get_occupied_seats(
        self,
        event_id: int,
        day: date,
        exclude_order_id: str | None = None,
    ) -> list[str]:
        ...

    @abstractmethod
    def delete_by_order_id(self, order_id: str):
        ...


class PersonRepository(ABC):
    @abstractmethod
    def find_by_document(self, nit: str) -> dict:
        ...


class CampWeekRepository(ABC):
    @abstractmethod
    def get_by_event(self, event_id: int) -> list:
        """Retorna semanas activas de un evento Camp."""
        ...

    @abstractmethod
    def get_by_id(self, week_id: int):
        """Retorna una semana por su ID."""
        ...

    @abstractmethod
    def decrease_stock(self, week_id: int, qty: int = 1):
        """
        Descuenta cupos de forma atómica.
        Lanza ValueError si no hay stock suficiente.
        """
        ...

    @abstractmethod
    def restore_stock(self, week_id: int, qty: int = 1):
        """
        Restaura cupos (al eliminar una orden PENDING).
        """
        ...


class CampPackageRepository(ABC):
    @abstractmethod
    def get_by_event(self, event_id: int) -> list:
        """Retorna paquetes activos de un evento Camp."""
        ...

    @abstractmethod
    def get_by_id(self, package_id: int):
        """Retorna un paquete por su ID."""
        ...


class CampEnrollmentRepository(ABC):
    @abstractmethod
    def create(self, enrollment):
        """Persiste una inscripción de Camp."""
        ...

    @abstractmethod
    def get_by_order_id(self, order_id: str) -> list:
        """Retorna todas las inscripciones de una orden."""
        ...

    @abstractmethod
    def delete_by_order_id(self, order_id: str):
        """Elimina todas las inscripciones de una orden."""
        ...
