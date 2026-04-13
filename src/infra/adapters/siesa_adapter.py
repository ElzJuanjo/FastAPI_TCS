import os
import re
import logging
import json
from datetime import datetime

from zeep import Client
from zeep.transports import Transport
from zeep.helpers import serialize_object
from requests import Session

from src.infra.config.database import get_mssql_connection
from src.infra.config.settings import get_settings

logger = logging.getLogger("siesa")
settings = get_settings()


# ==========================================================
# HELPERS
# ==========================================================

def sanitize_siesa_text(value: str, max_len=250) -> str:
    if not value:
        return ""
    value = re.sub(r"[^\x20-\x7E]", "", value)
    value = (
        value.replace("&", "Y")
        .replace("<", "")
        .replace(">", "")
        .replace('"', "")
        .replace("'", "")
    )
    return value[:max_len].upper()


def _now_colombia():
    return datetime.now(settings.TIMEZONE)


# ==========================================================
# CONFIG POR SERVICIO
# ==========================================================

# Mapeo event_id → school_services.id
EVENT_SERVICE_MAP = {
    1: 340,
    2: 443, 
}

DEFAULT_SERVICE_ID = 340


def get_service_siesa_config(event_id: int = None):
    service_id = EVENT_SERVICE_MAP.get(event_id, DEFAULT_SERVICE_ID)

    conn = get_mssql_connection()
    cursor = conn.cursor()

    query = f"""
    SELECT
        id_co,
        siesa_service_id,
        siesa_cc,
        siesa_id_motivo,
        id_tipo_cli,
        id_cond_pago,
        id_auxiliar_docto_cruce,
        id_co_docto_cruce,
        id_un_docto_cruce,
        id_caja,
        id_fe,
        id_un,
        siesa_seller_id,
        siesa_seller_tercero_id
    FROM ecampus.dbo.school_services
    WHERE id = {service_id}
    """

    cursor.execute(query)
    row = cursor.fetchone()

    if not row:
        cursor.close()
        conn.close()
        raise ValueError(f"Servicio {service_id} (event_id={event_id}) sin configuración SIESA")

    columns = [column[0] for column in cursor.description]
    config = dict(zip(columns, row))

    cursor.close()
    conn.close()
    return config


# ==========================================================
# NORMALIZACIÓN DE MEDIO DE PAGO
# ==========================================================

# ── TARJETAS (SIESA → TCD) ──
# Incluye: franquicias de tarjeta crédito/débito de PlaceToPay + Wompi
_CARD_KEYWORDS = {
    # Wompi
    "CARD",
    # PlaceToPay - paymentMethod / paymentMethodName / franchise
    "VISA", "MASTER", "MASTERCARD", "DINERS", "AMEX",
    "AMERICAN EXPRESS", "DISCOVER", "MAESTRO",
    # PlaceToPay - tarjetas Colombia
    "CODENSA", "EXITO", "ALKOSTO", "SOMOS", "CAFAM",
    # PlaceToPay - tarjetas regionales
    "ATH_CARD", "TELERED", "EBT", "EBTCH", "EBTRG", "ALIA",
    # PlaceToPay - franchise codes (CR_ = crédito, DB_ = débito)
    "CR_VS", "CR_MC", "CR_DN", "CR_AM", "CR_DC",
    "DB_VS", "DB_MC", "DB_DN",
    "RM_MC",  # recurrente Mastercard
    "VISA_ELECTRON",
    # Genéricos
    "CREDIT", "DEBIT", "TARJETA",
}

# ── TRANSFERENCIAS / PSE / EFECTIVO (SIESA → CB5) ──
_TRANSFER_KEYWORDS = {
    # Wompi
    "BANCOLOMBIA_TRANSFER", "BANCOLOMBIA_COLLECT",
    "PSE", "NEQUI", "DAVIPLATA",
    # PlaceToPay - Colombia
    "BANCOLOMBIA", "BANCO_BOGOTA",
    "ATH", "GANA",
    "PROCESA",  # Billetera Compensar
    # PlaceToPay - otros países
    "SAFETYPAY", "SAFETY PAY",
    "PAGOEFECTIVO", "PAGO EFECTIVO",
    "PAYPAL",
    "ATHMV",   # ATH Móvil Puerto Rico
    "EBACH",   # ACH Puerto Rico
    # Genéricos
    "ACH", "TRANSFER", "EFECTIVO", "EFECTY", "BALOTO",
    "SU RED", "BANCO", "CUENTAS",
}


def _normalize_payment_method(payment_method: str | None) -> str:
    """
    Normaliza el método de pago de cualquier gateway a CARD o TRANSFER.
    Si no se puede determinar, asume TRANSFER (CB5 es más seguro en SIESA).
    """
    if not payment_method:
        return "TRANSFER"

    upper = payment_method.upper().strip()

    # Primero checar tarjeta (más específico)
    for kw in _CARD_KEYWORDS:
        if kw in upper:
            return "CARD"

    # Luego transferencia
    for kw in _TRANSFER_KEYWORDS:
        if kw in upper:
            return "TRANSFER"

    # Default: transferencia
    return "TRANSFER"


# ==========================================================
# SIESA SERVICE
# ==========================================================

class SiesaService:

    def __init__(self):
        wsdl_url = settings.SIESA_WSDL_URL
        if not wsdl_url:
            raise ValueError("SIESA_WSDL_URL no configurado")

        session = Session()
        session.verify = False

        transport = Transport(session=session, timeout=30)
        self.client = Client(wsdl_url, transport=transport)

        self.F_CIA = settings.SIESA_F_CIA
        self.ID_SUCURSAL = settings.SIESA_ID_SUCURSAL

    # ==========================================================
    # FACTURA
    # ==========================================================

    def generar_factura(self, payment, order):
        if not order.siesa_id:
            return {"success": False, "message": "Orden sin siesa_id"}

        config = get_service_siesa_config(order.event_id)
        now = _now_colombia()
        fecha = now.strftime("%Y%m%d")

        logger.info(f"Iniciando factura SIESA | pago={payment.id}")

        # Determinar cantidad: tickets si existen, sino attendees
        ticket_count = len(order.tickets) if order.tickets else 0
        attendee_count = len(order.attendees) if order.attendees else 0

        if ticket_count > 0:
            cantidad = sum(t.amount for t in order.tickets)
        else:
            cantidad = attendee_count if attendee_count > 0 else 1

        movimientos = {
            "Factura_Financiera_Movimiento": [
                {
                    "F320_CANTIDAD": str(cantidad),
                    "F320_ID_CO_MOVTO": config["id_co"],
                    "F320_ID_UN_MOVTO": config["id_un"],
                    "F320_ID_MOTIVO": config["siesa_id_motivo"],
                    "F320_ID_SERVICIO": config["siesa_service_id"],
                    "F320_ID_CCOSTO_MOVTO": config["siesa_cc"],
                    "F320_ID_SUCURSAL_CLIENTE": self.ID_SUCURSAL,
                    "F320_ID_TERCERO_MOVTO": str(order.siesa_id),
                    "F320_VLR_BRUTO": str(order.total_amount),
                    "F320_VLR_DSCTO_1": "0",
                    "F320_VLR_DSCTO_2": "0",
                    "F320_NOTAS": sanitize_siesa_text(
                        f"Evento {order.event.title}"
                    ),
                }
            ]
        }

        # Construir nota del pago según gateway
        gateway_ref = ""
        if payment.gateway == "PLACETOPAY":
            gateway_ref = f"PlaceToPay {payment.placetopay_request_id or 'N/A'}"
        else:
            gateway_ref = f"Wompi {payment.wompi_transaction_id or 'N/A'}"

        factura_data = {
            "F350_ID_CO": config["id_co"],
            "F350_ID_TIPO_DOCTO": "FES",
            "F350_ID_CLASE_DOCTO": "22",
            "F350_CONSEC_DOCTO": "",
            "F350_FECHA": fecha,
            "F350_ID_TERCERO": str(order.siesa_id),
            "F350_IND_ESTADO": "1",
            "F350_NOTAS": sanitize_siesa_text(
                f"Pago evento {order.event.title} | {gateway_ref}"
            ),
            "F311_ID_SUCURSAL_CLI": self.ID_SUCURSAL,
            "F311_ID_TIPO_CLI": config["id_tipo_cli"],
            "F311_ID_TERCERO_VENDEDOR": config["siesa_seller_tercero_id"],
            "F311_ID_COND_PAGO": config["id_cond_pago"],
            "F311_ID_MONEDA_DOCTO": "COP",
            "F_CIA": self.F_CIA,
            "MOVIMIENTOS": movimientos,
        }

        try:
            response = self.client.service.Financiera_Factura(
                Factura=factura_data
            )
            return self._procesar_respuesta_documento(response, "factura")
        except Exception as e:
            logger.error("Error llamando Financiera_Factura")
            return {"success": False, "message": str(e)}

    # ==========================================================
    # RECIBO
    # ==========================================================

    def generar_recibo_caja(self, payment, order, invoice_number):
        if not invoice_number:
            return {"success": False, "message": "Número de factura requerido"}

        config = get_service_siesa_config(order.event_id)
        now = _now_colombia()
        fecha = now.strftime("%Y%m%d")

        logger.info(f"Iniciando recibo SIESA | pago={payment.id}")

        consec_only = (
            invoice_number.split("-")[-1]
            if "-" in invoice_number
            else invoice_number
        )

        payment_extra = self.get_raw_response(payment)

        # Normalizar método de pago independiente del gateway
        normalized_method = _normalize_payment_method(payment.payment_method)

        if normalized_method == "CARD":
            medio_pago = "TCD"
            nro_cuenta = payment_extra.get("last_four", "")
            nro_autorizacion = payment_extra.get("external_identifier", "")[:10]
            referencia_otros = ""
        else:
            medio_pago = "CB5"
            nro_cuenta = ""
            nro_autorizacion = payment_extra.get("external_identifier", "")[:10]
            referencia_otros = payment_extra.get("external_identifier", "")[:8]

        # Nota según gateway
        gateway_ref = ""
        if payment.gateway == "PLACETOPAY":
            gateway_ref = f"PlaceToPay {payment.placetopay_request_id or 'N/A'}"
        else:
            gateway_ref = f"Wompi {payment.wompi_transaction_id or 'N/A'}"

        recibo_data = {
            "F350_ID_CO": config["id_co"],
            "F350_ID_TIPO_DOCTO": "RCV",
            "F350_ID_CLASE_DOCTO": "13",
            "F350_CONSEC_DOCTO": "",
            "F350_FECHA": fecha,
            "F350_ID_TERCERO": str(order.siesa_id),
            "F350_IND_ESTADO": "1",
            "F350_NOTAS": sanitize_siesa_text(
                f"Pago evento {order.event.title} | {gateway_ref}"
            ),
            "F357_FECHA_RECAUDO": fecha,
            "F357_ID_CAJA": config["id_caja"],
            "F357_ID_FE": config["id_fe"],
            "F357_ID_MONEDA_APLICAR": "COP",
            "F357_ID_MONEDA_INGRESO": "COP",
            "F357_REFERENCIA": (
                payment.wompi_transaction_id
                or payment.placetopay_request_id
                or "N/A"
            ),
            "F357_VALOR_APLICAR_REAL": str(order.total_amount),
            "F357_VALOR_INGRESO": str(order.total_amount),
            "F357_ID_COBRADOR": config["siesa_seller_id"],
            "F357_IND_VALIDA_MEDPAGO": "1",
            "F353_ID_AUXILIAR_DOCTO_CRUCE": config["id_auxiliar_docto_cruce"],
            "F353_CONSEC_DOCTO_CRUCE": consec_only,
            "F353_ID_CO_DOCTO_CRUCE": config["id_co_docto_cruce"],
            "F353_ID_TIPO_DOCTO_CRUCE": "FES",
            "F353_ID_SUCURSAL_DOCTO_CRUCE": self.ID_SUCURSAL,
            "F353_ID_UN_DOCTO_CRUCE": config["id_un_docto_cruce"],
            "F353_NRO_CUOTA_CRUCE": "0",
            "F354_VALOR_CR": str(order.total_amount),
            "F354_VALOR_APLICADO_PP": "0",
            "F354_VALOR_APROVECHA": "0",
            "F354_VALOR_RETENCION": "0",
            "F358_ID_MEDIOS_PAGO": medio_pago,
            "F358_NRO_CUENTA": nro_cuenta,
            "F358_NRO_AUTORIZACION": nro_autorizacion,
            "F358_REFERENCIA_OTROS": referencia_otros,
            "F358_NOTAS": sanitize_siesa_text(
                f"Pago evento {order.event.title} | {gateway_ref}"
            ),
            "F358_FECHA_CONSIGNACION": fecha,
            "F358_FECHA_VCTO": fecha,
            "F358_VALOR": str(order.total_amount),
            "F358_ID_TERCERO": str(order.siesa_id),
            "F_CIA": self.F_CIA,
        }

        try:
            response = self.client.service.Recibo_de_caja(Recibo=recibo_data)
            return self._procesar_respuesta_documento(response, "recibo")
        except Exception as e:
            logger.error("Error llamando Recibo_de_caja")
            return {"success": False, "message": str(e)}

    # ==========================================================
    # CONSECUTIVO
    # ==========================================================

    def obtener_consecutivo_generado(
        self, tipo_doc, tercero_id, total_db, nota_like, nro_autorizacion=""
    ):
        conn = get_mssql_connection()
        cursor = conn.cursor()

        join_mp = ""
        autorizacion_filter = ""

        if tipo_doc == "RCV":
            join_mp = """
            INNER JOIN t358_co_relacion_medios_pago MP
                ON MP.F358_ROWID_DOCTO = DC.F350_ROWID
            """
            autorizacion_filter = (
                f"AND MP.F358_NRO_AUTORIZACION = ''{nro_autorizacion}''"
            )

        query = f"""
        SELECT
            ID_CO,
            ID_TIPO_DOCTO,
            CONSEC_DOCTO
        FROM OPENQUERY(CSERPDB,
        '
            SELECT TOP 1
                DC.F350_ID_CO         AS ID_CO,
                DC.F350_ID_TIPO_DOCTO AS ID_TIPO_DOCTO,
                DC.F350_CONSEC_DOCTO  AS CONSEC_DOCTO

            FROM t350_co_docto_contable DC

            INNER JOIN t200_mm_terceros T
                ON T.F200_ROWID = DC.F350_ROWID_TERCERO

            {join_mp}

            WHERE
                DC.F350_ID_TIPO_DOCTO = ''{tipo_doc}''
                AND DC.F350_TOTAL_DB = {total_db}

                {autorizacion_filter}

                AND T.F200_ID = ''{tercero_id}''
                AND T.F200_ID_CIA = 1
                AND T.F200_IND_ESTADO = 1

                AND DC.F350_NOTAS LIKE ''%{nota_like}%''

            ORDER BY DC.F350_CONSEC_DOCTO DESC
        ')
        """

        cursor.execute(query)
        rows = cursor.fetchall()

        cursor.close()
        conn.close()

        if not rows:
            return None

        id_co, tipo_docto, consecutivo = rows[0]
        consecutivo_str = str(consecutivo).zfill(8)

        return f"{id_co}-{tipo_docto}-{consecutivo_str}"

    def get_raw_response(self, payment):
        raw_data = {}
        if payment.raw_response:
            try:
                raw_data = (
                    json.loads(payment.raw_response)
                    if isinstance(payment.raw_response, str)
                    else payment.raw_response
                )
            except Exception as e:
                logger.warning(f"No se pudo parsear raw_response: {e}")
                raise Exception(f"Error parseando raw_response: {str(e)}")

        # ── Wompi ──
        # Estructura: { payment_method: { extra: { external_identifier, ... } } }
        if payment.gateway == "WOMPI":
            return raw_data.get("payment_method", {}).get("extra", {})

        # ── PlaceToPay ──
        # Estructura: { payment: [{ authorization, processorFields: [{keyword, value}], ... }] }
        if payment.gateway == "PLACETOPAY":
            transactions = raw_data.get("payment", [])
            if not transactions or not isinstance(transactions, list):
                return {}

            tx = transactions[0]

            # processorFields es un array [{keyword, value}, ...]
            proc_fields = {}
            for field in (tx.get("processorFields") or []):
                proc_fields[field.get("keyword", "")] = field.get("value", "")

            return {
                "franchise": tx.get("franchise", ""),
                "last_four": proc_fields.get("lastDigits", ""),
                "external_identifier": tx.get("authorization", ""),
            }

        return raw_data.get("payment_method", {}).get("extra", {})

    # ==========================================================
    # RESPUESTAS
    # ==========================================================

    def _join_errors(self, errores):
        if isinstance(errores, list):
            return " | ".join(str(e) for e in errores)
        return str(errores)

    def _procesar_respuesta_documento(self, response, tipo_documento):
        data = serialize_object(response)

        logger.info("====== RESPUESTA SIESA SERIALIZED ======")
        logger.info(f"type(data): {type(data)}")
        logger.info(f"data: {data}")

        if isinstance(data, list):
            if not data or all(x is None for x in data):
                return {
                    "success": True,
                    "message": f"{tipo_documento.capitalize()} generada correctamente",
                }
            return {"success": False, "message": self._join_errors(data)}

        if isinstance(data, dict):
            errores = data.get("Errores")
            if errores:
                return {"success": False, "message": self._join_errors(errores)}

        return {"success": False, "message": f"Respuesta inesperada SIESA: {data}"}


# Singleton con manejo de error
try:
    siesa_service = SiesaService()
except Exception:
    logger.error("No se pudo inicializar SIESA")
    siesa_service = None
