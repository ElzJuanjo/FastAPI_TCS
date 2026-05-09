from sqlalchemy.orm import Session

from src.domain.entities.order_camp_enrollment import OrderCampEnrollment
from src.domain.repositories import CampEnrollmentRepository


class CampEnrollmentRepositorySQL(CampEnrollmentRepository):
    def __init__(self, db: Session):
        self.db = db

    def create(self, enrollment: OrderCampEnrollment):
        self.db.add(enrollment)
        self.db.flush()
        return enrollment

    def get_by_order_id(self, order_id: str) -> list[OrderCampEnrollment]:
        return (
            self.db.query(OrderCampEnrollment)
            .filter(OrderCampEnrollment.order_id == order_id)
            .all()
        )

    def delete_by_order_id(self, order_id: str):
        enrollments = self.get_by_order_id(order_id)
        for e in enrollments:
            self.db.delete(e)
        self.db.flush()
