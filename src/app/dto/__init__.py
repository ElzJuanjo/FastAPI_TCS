from pydantic import BaseModel, Field, model_validator
from typing import Optional
from datetime import date


# ===========================
# EVENT
# ===========================

class EventCreate(BaseModel):
    title: str
    date: str
    location: Optional[str] = None
    ticket_price: int
    staff_price: int
    combo_price: int
    description: Optional[str] = None
    stock: int
    is_active: bool = True


class EventResponse(BaseModel):
    id: int
    title: str
    date: str
    location: Optional[str]
    ticket_price: int
    staff_price: int
    combo_price: int
    description: Optional[str]
    stock: int

    class Config:
        from_attributes = True


# ===========================
# BUYER
# ===========================

class BuyerData(BaseModel):
    nit_type: str
    nit: str
    first_name: str
    middle_name: Optional[str] = None
    last_name_1: str
    last_name_2: Optional[str] = None
    birth_date: Optional[str] = None
    email: str
    cell_phone: str
    person_source: str
    event_id: int
    siesa_id: str
    family_id: Optional[str] = None


# ===========================
# ATTENDEE (legacy - carreras)
# ===========================

class AttendeeData(BaseModel):
    nit_type: str = "CC"
    nit: str
    first_name: str
    middle_name: Optional[str] = None
    last_name_1: str
    last_name_2: Optional[str] = None
    birth_date: Optional[str] = None
    email: Optional[str] = None
    cell_phone: str
    person_source: str
    is_adult: bool = False
    shirt_size: str
    age_range: str
    eps: Optional[str] = None
    emergency_contact_name: Optional[str] = None
    emergency_contact_phone: Optional[str] = None
    medical_info: Optional[str] = None


# ===========================
# TICKETS (teatro/cine)
# ===========================

class TicketData(BaseModel):
    day: date = Field(..., description="Dia del evento: YYYY-MM-DD")
    seats: str = Field(..., description="Asientos separados por coma: A1,A2,A3")
    amount: int = Field(..., gt=0, description="Cantidad total de asientos")


# ===========================
# CAMP
# ===========================

class CampChildData(BaseModel):
    child_first_name: str = Field(..., description="Nombre del menor")
    child_last_name: str = Field(..., description="Apellido del menor")
    child_nit_type: Optional[str] = Field(None, description="Tipo de documento del menor (CC, TI, RC, etc.)")
    child_nit: Optional[str] = Field(None, description="Numero de documento del menor")

    age_group: str = Field(
        ...,
        description="Grupo etario definido por el evento (ej: K4_1ST, 2ND_3RD, 4TH_5TH)"
    )

    enrollment_type: str = Field(
        ...,
        description="Tipo de inscripcion: WEEK | PACKAGE | DAY (extensible por evento)"
    )

    camp_week_id: Optional[int] = None
    camp_package_id: Optional[int] = None
    individual_date: Optional[date] = None

    @model_validator(mode="after")
    def validate_enrollment_fields(self):
        if self.enrollment_type == "WEEK" and self.camp_week_id is None:
            raise ValueError("camp_week_id es requerido cuando enrollment_type es WEEK")
        if self.enrollment_type == "PACKAGE" and self.camp_package_id is None:
            raise ValueError("camp_package_id es requerido cuando enrollment_type es PACKAGE")
        if self.enrollment_type == "DAY" and self.individual_date is None:
            raise ValueError("individual_date es requerida cuando enrollment_type es DAY")
        return self


# ===========================
# ORDER
# ===========================

class OrderCreateRequest(BaseModel):
    buyer: BuyerData
    attendees: Optional[list[AttendeeData]] = None
    tickets: Optional[TicketData] = None
    camp_children: Optional[list[CampChildData]] = None


class OrderResponse(BaseModel):
    order_id: str
    status: str
    total: int
    event_id: int
    family_id: Optional[str] = None
    buyer: dict
    attendees: Optional[list[dict]] = None
    tickets: Optional[dict] = None
    camp_enrollments: Optional[list[dict]] = None
    created_at: str


# ===========================
# PAYMENT
# ===========================

class PaymentInitRequest(BaseModel):
    gateway: str = Field(default="WOMPI", description="Pasarela de pago: WOMPI | PLACETOPAY")


class PaymentInitResponse(BaseModel):
    payment_id: int
    order_id: str
    gateway: str
    redirect_url: Optional[str] = None
    amount: Optional[int] = None
    currency: Optional[str] = None
    status: Optional[str] = None
    reference: Optional[str] = None
    public_key: Optional[str] = None
    integrity_signature: Optional[str] = None
    process_url: Optional[str] = None
    request_id: Optional[str] = None
