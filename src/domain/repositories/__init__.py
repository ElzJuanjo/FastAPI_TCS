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