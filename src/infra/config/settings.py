import os
import pytz
from pydantic_settings import BaseSettings
from functools import lru_cache
from typing import List, Optional


class Settings(BaseSettings):
    # ===========================
    # DATABASE
    # ===========================
    MSSQL_USER: str = ""
    MSSQL_PASSWORD: str = ""
    MSSQL_HOST: str = ""
    MSSQL_PORT: str = "1433"
    MSSQL_STORAGE: str = ""
    MSSQL_DB: str = ""
    MSSQL_DRIVER: str = "ODBC Driver 18 for SQL Server"

    @property
    def DATABASE_URL(self) -> str:
        driver = self.MSSQL_DRIVER.replace(" ", "+")
        return (
            f"mssql+pyodbc://{self.MSSQL_USER}:{self.MSSQL_PASSWORD}"
            f"@{self.MSSQL_HOST}:{self.MSSQL_PORT}/{self.MSSQL_STORAGE}"
            f"?driver={driver}&TrustServerCertificate=yes"
        )

    @property
    def PYODBC_CONN_STR(self) -> str:
        return (
            f"DRIVER={{{self.MSSQL_DRIVER}}};"
            f"SERVER={self.MSSQL_HOST},{self.MSSQL_PORT};"
            f"DATABASE={self.MSSQL_DB};"
            f"UID={self.MSSQL_USER};"
            f"PWD={self.MSSQL_PASSWORD};"
            "TrustServerCertificate=yes;"
        )

    # ===========================
    # SECURITY
    # ===========================
    SUPPORT_KEY: str = ""

    # ===========================
    # CORS
    # ===========================
    # URL principal del frontend para redirect de gateway (Wompi).
    FRONTEND_URL: Optional[str] = None

    # Lista de orígenes permitidos por CORS, separados por coma.
    CORS_ORIGINS: str = "http://localhost:3000"

    @property
    def cors_origins_list(self) -> List[str]:
        return [
            origin.strip()
            for origin in self.CORS_ORIGINS.split(",")
            if origin.strip()
        ]

    # ===========================
    # WOMPI
    # ===========================
    WOMPI_API_URL: str = ""
    WOMPI_PUBLIC_KEY: str = ""
    WOMPI_PRIVATE_KEY: str = ""
    WOMPI_SECRET_EVENT: str = ""
    WOMPI_SECRET_INTEGRITY: str = ""

    # ===========================
    # PLACETOPAY
    # ===========================
    PLACETOPAY_URL: str = ""
    PLACETOPAY_LOGIN: str = ""
    PLACETOPAY_TRANKEY: str = ""
    PLACETOPAY_RETURN_URL: str = ""

    # ===========================
    # SIESA
    # ===========================
    SIESA_WSDL_URL: str = ""
    SIESA_F_CIA: str = ""
    SIESA_ID_SUCURSAL: str = ""

    # ===========================
    # MAIL
    # ===========================
    MAIL_SERVER: str = ""
    MAIL_PORT: int = 587
    MAIL_USE_TLS: bool = True
    MAIL_USE_SSL: bool = False

    # ---------- Perfil TICKETS (teatro/cine) ----------
    MAIL_USERNAME_TICKETS: str = ""
    MAIL_PASSWORD_TICKETS: str = ""
    MAIL_DEFAULT_SENDER_TICKETS: str = ""
    COMPANY_LOGO_URL_TICKETS: str = ""
    COMPANY_LOGO_FILE_TICKETS: str = "logos_tickets.png"

    # ---------- Perfil ATTENDEES (carreras) ----------
    MAIL_USERNAME_ATTENDEES: str = ""
    MAIL_PASSWORD_ATTENDEES: str = ""
    MAIL_DEFAULT_SENDER_ATTENDEES: str = ""
    COMPANY_LOGO_URL_ATTENDEES: str = ""
    COMPANY_LOGO_FILE_ATTENDEES: str = "logos_attendees.png"

    # ---------- Perfil CAMP (TCS Camp) ----------
    MAIL_USERNAME_CAMP: str = ""
    MAIL_PASSWORD_CAMP: str = ""
    MAIL_DEFAULT_SENDER_CAMP: str = ""
    COMPANY_LOGO_URL_CAMP: str = ""
    COMPANY_LOGO_FILE_CAMP: str = "logos_camp.png"

    # ===========================
    # CAMP
    # ===========================
    # Precio del día individual en pesos COP.
    # Parametrizado para ajustar sin redeploy.
    CAMP_DAY_PRICE: int = 200_000

    # ===========================
    # LOGGING
    # ===========================
    LOG_LEVEL: str = "INFO"

    # ===========================
    # SEAT RESERVATION
    # ===========================
    SEAT_RESERVATION_TTL_MINUTES: int = 15

    # ===========================
    # TIMEZONE
    # ===========================
    @property
    def TIMEZONE(self):
        return pytz.timezone("America/Bogota")

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


@lru_cache()
def get_settings() -> Settings:
    return Settings()
