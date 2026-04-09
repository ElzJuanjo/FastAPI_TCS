from sqlalchemy.orm import Session
from src.domain.entities.payment import Payment
from src.domain.repositories import PaymentRepository


class PaymentRepositorySQL(PaymentRepository):
    def __init__(self, db: Session):
        self.db = db

    def get_by_order_id(self, order_id: str):
        return (
            self.db.query(Payment)
            .filter_by(order_id=order_id)
            .first()
        )

    def get_approved(self) -> list:
        return (
            self.db.query(Payment)
            .filter_by(status="APPROVED")
            .all()
        )

    def create(self, payment: Payment):
        self.db.add(payment)
        self.db.commit()
        self.db.refresh(payment)
        return payment

    def update(self, payment: Payment):
        self.db.commit()
        return payment

    def delete(self, payment: Payment):
        self.db.delete(payment)
        self.db.commit()
