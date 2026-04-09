from sqlalchemy.orm import Session
from src.domain.entities.order import Order
from src.domain.repositories import OrderRepository


class OrderRepositorySQL(OrderRepository):
    def __init__(self, db: Session):
        self.db = db

    def get_by_id(self, order_id: str):
        return self.db.query(Order).get(order_id)

    def get_by_person(self, nit_type: str, nit: str):
        return (
            self.db.query(Order)
            .filter_by(nit_type=nit_type, nit=nit)
            .order_by(Order.created_at.desc())
            .first()
        )

    def get_all(self) -> list:
        return (
            self.db.query(Order)
            .order_by(Order.created_at.desc())
            .all()
        )

    def create(self, order: Order):
        self.db.add(order)
        self.db.flush()
        return order

    def update(self, order: Order):
        self.db.flush()
        return order

    def delete(self, order: Order):
        self.db.delete(order)
        self.db.commit()
