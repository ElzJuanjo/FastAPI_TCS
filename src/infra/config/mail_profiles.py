"""
Resolver de perfil de correo por línea de negocio.

Centraliza la decisión de qué credenciales SMTP, sender y logo usar
según el contenido de la orden:
  - tickets  -> perfil TICKETS  (teatro/cine)
  - attendees -> perfil ATTENDEES (carreras)

Un único punto de decisión = fácil de testear y de extender a nuevas
líneas de negocio sin tocar los adapters.
"""

from dataclasses import dataclass
from typing import Literal

from src.infra.config.settings import get_settings

ProfileKind = Literal["tickets", "attendees"]


@dataclass(frozen=True)
class MailProfile:
    kind: ProfileKind
    username: str
    password: str
    default_sender: str
    logo_url: str
    logo_filename: str 


def resolve_profile_kind(order) -> ProfileKind:
    """
    Regla de negocio: si la orden tiene tickets, es perfil 'tickets';
    en caso contrario (attendees o vacío) cae a 'attendees'.
    Mantener aquí la regla evita duplicarla en email y receipt.
    """
    if getattr(order, "tickets", None):
        return "tickets"
    return "attendees"


def get_mail_profile(order) -> MailProfile:
    settings = get_settings()
    kind = resolve_profile_kind(order)

    if kind == "tickets":
        return MailProfile(
            kind="tickets",
            username=settings.MAIL_USERNAME_TICKETS,
            password=settings.MAIL_PASSWORD_TICKETS,
            default_sender=settings.MAIL_DEFAULT_SENDER_TICKETS,
            logo_url=settings.COMPANY_LOGO_URL_TICKETS,
            logo_filename=settings.COMPANY_LOGO_FILE_TICKETS,
        )

    return MailProfile(
        kind="attendees",
        username=settings.MAIL_USERNAME_ATTENDEES,
        password=settings.MAIL_PASSWORD_ATTENDEES,
        default_sender=settings.MAIL_DEFAULT_SENDER_ATTENDEES,
        logo_url=settings.COMPANY_LOGO_URL_ATTENDEES,
        logo_filename=settings.COMPANY_LOGO_FILE_ATTENDEES,
    )