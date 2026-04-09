from pydantic import BaseModel, Field
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
    """Datos de boletos para teatro/cine."""
    day: date = Field(..., description="Día del evento: YYYY-MM-DD")
    seats: str = Field(..., description="Asientos separados por coma: A1,A2,A3")
    amount: int = Field(..., gt=0, description="Cantidad total de asientos")


# ===========================
# ORDER
# ===========================

class OrderCreateRequest(BaseModel):
    """
    Soporta ambos tipos de evento:
    - Carreras: buyer + attendees
    - Teatro/Cine: buyer + tickets
    """
    buyer: BuyerData
    attendees: Optional[list[AttendeeData]] = None
    tickets: Optional[TicketData] = None


class OrderResponse(BaseModel):
    order_id: str
    status: str
    total: int
    event_id: int
    family_id: Optional[str] = None
    buyer: dict
    attendees: Optional[list[dict]] = None
    tickets: Optional[dict] = None
    created_at: str


# ===========================
# PAYMENT
# ===========================

class PaymentInitRequest(BaseModel):
    gateway: str = Field(
        default="WOMPI",
        description="Pasarela de pago: WOMPI | PLACETOPAY",
    )


class PaymentInitResponse(BaseModel):
    payment_id: int
    order_id: str
    gateway: str
    # Wompi fields
    redirect_url: Optional[str] = None
    amount: Optional[int] = None
    currency: Optional[str] = None
    status: Optional[str] = None
    reference: Optional[str] = None
    public_key: Optional[str] = None
    integrity_signature: Optional[str] = None
    # PlaceToPay fields
    process_url: Optional[str] = None
    request_id: Optional[str] = None