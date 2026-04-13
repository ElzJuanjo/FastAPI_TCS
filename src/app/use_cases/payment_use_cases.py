import logging
from sqlalchemy.orm import Session

from src.domain.entities.payment import Payment
from src.domain.entities.order import Order
from src.domain.entities.event import Event
from src.infra.adapters.payment_repository import PaymentRepositorySQL
from src.infra.adapters.event_repository import EventRepositorySQL
from src.infra.adapters.wompi_adapter import generate_wompi_integrity_signature
from src.infra.adapters import placetopay_adapter
from src.infra.adapters.email_adapter import send_payment_confirmation_email
from src.infra.config.settings import get_settings

logger = logging.getLogger("payments")
settings = get_settings()

try:
    from src.infra.adapters.siesa_adapter import siesa_service
    SIESA_AVAILABLE = siesa_service is not None
except ImportError:
    SIESA_AVAILABLE = False
    siesa_service = None


class PaymentUseCases:
    def __init__(self, db: Session):
        self.db = db
        self.payment_repo = PaymentRepositorySQL(db)
        self.event_repo = EventRepositorySQL(db)

    def get_approved(self):
        return self.payment_repo.get_approved()

    # ===========================================
    # INIT PAYMENT
    # ===========================================
    def init_payment(self, order_id: str, gateway: str = "WOMPI") -> dict:
        order = self.db.query(Order).get(order_id)
        if not order:
            raise ValueError("Orden no encontrada")

        event = self.db.query(Event).get(order.event_id)
        if not event:
            raise ValueError("Evento no encontrado")

        # Validar stock según tipo
        if order.tickets:
            ticket_count = sum(t.amount for t in order.tickets)
            if ticket_count > event.stock:
                raise ValueError("La cantidad de boletos supera el stock disponible")
        elif order.attendees:
            if len(order.attendees) > event.stock:
                raise ValueError("La cantidad de asistentes supera el stock disponible")

        # Limpiar pago previo si no está aprobado
        existing = self.payment_repo.get_by_order_id(order_id)
        if existing:
            if existing.status == "APPROVED":
                raise ValueError("Ya existe un pago aprobado para esta orden")
            self.payment_repo.delete(existing)

        # Crear payment
        payment = Payment(
            order_id=order.id,
            amount=order.total_amount,
            gateway=gateway.upper(),
        )
        self.payment_repo.create(payment)

        if gateway.upper() == "PLACETOPAY":
            return self._init_placetopay(payment, order)
        else:
            return self._init_wompi(payment, order)

    def _init_wompi(self, payment: Payment, order: Order) -> dict:
        amount_in_cents = payment.amount * 100

        integrity_signature = generate_wompi_integrity_signature(
            reference=order.id,
            amount_in_cents=amount_in_cents,
            currency=payment.currency,
        )

        return {
            "payment_id": payment.id,
            "order_id": order.id,
            "gateway": "WOMPI",
            "redirect_url": settings.FRONTEND_URL,
            "amount": amount_in_cents,
            "currency": payment.currency,
            "status": payment.status,
            "reference": order.id,
            "public_key": settings.WOMPI_PUBLIC_KEY,
            "integrity_signature": integrity_signature,
        }

    def _init_placetopay(self, payment: Payment, order: Order) -> dict:
        buyer_name = f"{order.first_name} {order.last_name_1}"

        result = placetopay_adapter.create_session(
            reference=order.id,
            description=f"Pago evento - Orden #{order.id}",
            amount=payment.amount,
            currency=payment.currency,
            buyer_name=buyer_name,
            buyer_email=order.email,
        )

        # Guardar datos PlaceToPay
        payment.placetopay_request_id = result["request_id"]
        payment.placetopay_session_url = result["process_url"]
        self.db.commit()

        return {
            "payment_id": payment.id,
            "order_id": order.id,
            "gateway": "PLACETOPAY",
            "process_url": result["process_url"],
            "request_id": result["request_id"],
            "status": "PENDING",
        }

    # ===========================================
    # WOMPI WEBHOOK
    # ===========================================
    def process_wompi_webhook(self, transaction: dict):
        payment = self.payment_repo.get_by_order_id(
            transaction["reference"]
        )
        if not payment:
            raise ValueError("Pago no encontrado")

        payment.status = transaction["status"]
        payment.wompi_transaction_id = transaction["id"]
        payment.payment_method = transaction.get("payment_method_type")
        payment.raw_response = transaction

        if payment.status == "APPROVED":
            self._process_approved(payment)
        elif payment.status in ["DECLINED", "VOIDED", "ERROR"]:
            payment.order.status = "FAILED"
            logger.warning(f"Pago no aprobado {payment.id}")

        self.db.commit()

    # ===========================================
    # PLACETOPAY QUERY (para webhook o polling)
    # ===========================================
    def check_placetopay_status(self, order_id: str) -> dict:
        payment = self.payment_repo.get_by_order_id(order_id)
        if not payment:
            raise ValueError("Pago no encontrado")

        if payment.gateway != "PLACETOPAY":
            raise ValueError("Este pago no es de PlaceToPay")

        if not payment.placetopay_request_id:
            raise ValueError("No hay request_id de PlaceToPay")

        result = placetopay_adapter.query_session(
            payment.placetopay_request_id
        )

        payment.status = result["status"]
        payment.raw_response = result["raw"]

        if result["transaction_id"]:
            payment.wompi_transaction_id = result["transaction_id"]
        if result["payment_method"]:
            payment.payment_method = result["payment_method"]

        if payment.status == "APPROVED":
            self._process_approved(payment)
        elif payment.status in ["DECLINED", "VOIDED", "ERROR"]:
            payment.order.status = "FAILED"
            logger.warning(f"PlaceToPay pago rechazado {payment.id}")

        self.db.commit()

        return {
            "status": payment.status,
            "order_id": order_id,
            "payment_id": payment.id,
        }

    # ===========================================
    # PROCESS APPROVED (compartido)
    # ===========================================
    def _process_approved(self, payment: Payment):
        logger.info(f"Pago aprobado {payment.id}")

        payment.status = "APPROVED"
        payment.order.status = "PAID"

        # SIESA
        try:
            self._generar_documentos_siesa(payment)
        except Exception as e:
            logger.error(f"SIESA falló para pago {payment.id}")
            payment.siesa_error = str(e)

        # Stock + Email
        try:
            # Determinar cantidad para stock
            order = payment.order
            if order.tickets:
                quantity = sum(t.amount for t in order.tickets)
            else:
                quantity = len(order.attendees)

            self.event_repo.decrease_stock(order.event_id, quantity)

            import asyncio
            try:
                loop = asyncio.get_running_loop()
                loop.create_task(send_payment_confirmation_email(payment))
            except RuntimeError:
                asyncio.run(send_payment_confirmation_email(payment))

        except Exception:
            logger.error(f"Post-proceso falló para pago {payment.id}")

    def _generar_documentos_siesa(self, payment: Payment):
        if not siesa_service:
            raise ValueError("Servicio SIESA no inicializado")

        factura_result = None
        recibo_result = None

        logger.info(f"=== Generando documentos SIESA pago {payment.id} ===")

        order = (
            self.db.query(Order)
            .filter_by(id=payment.order_id)
            .first()
        )

        # Nota SIESA según evento
        nota_like = f"EVENTO {order.event.title}".upper()[:20] if order.event else "EVENTO"

        # Verificar recibo existente
        logger.info("Consultando recibo existente en SIESA...")

        extra = siesa_service.get_raw_response(payment)

        receipt_number = siesa_service.obtener_consecutivo_generado(
            tipo_doc="RCV",
            tercero_id=order.siesa_id,
            total_db=payment.amount,
            nota_like=nota_like,
            nro_autorizacion=extra.get("external_identifier", "")[:10],
        )

        if not receipt_number:
            # FACTURA
            logger.info(f"Generando factura SIESA pago {payment.id}")

            factura_result = siesa_service.generar_factura(payment, order)

            if not factura_result["success"]:
                raise Exception(f"Factura falló: {factura_result['message']}")

            invoice_number = siesa_service.obtener_consecutivo_generado(
                tipo_doc="FES",
                tercero_id=order.siesa_id,
                total_db=payment.amount,
                nota_like=nota_like,
            )

            if not invoice_number:
                raise Exception(
                    "Factura generada pero no se encontró consecutivo en SIESA"
                )

            payment.siesa_invoice_number = invoice_number
            logger.info(f"Factura generada pago {payment.id}: {invoice_number}")

            # RECIBO
            logger.info(f"Generando recibo SIESA pago {payment.id}")

            recibo_result = siesa_service.generar_recibo_caja(
                payment, order, payment.siesa_invoice_number
            )

            if not recibo_result["success"]:
                raise Exception(
                    f"Factura OK pero recibo falló: {recibo_result['message']}"
                )

            receipt_number = siesa_service.obtener_consecutivo_generado(
                tipo_doc="RCV",
                tercero_id=order.siesa_id,
                total_db=payment.amount,
                nota_like=nota_like,
                nro_autorizacion=extra.get("external_identifier", "")[:10],
            )

            if not receipt_number:
                raise Exception(
                    "Recibo generado pero no se encontró consecutivo en SIESA"
                )

            payment.siesa_receipt_number = receipt_number
            logger.info(f"Recibo generado pago {payment.id}: {receipt_number}")

        else:
            # Ya existe
            logger.info(f"Recibo ya existe en SIESA: {receipt_number}")
            invoice_number = siesa_service.obtener_consecutivo_generado(
                tipo_doc="FES",
                tercero_id=order.siesa_id,
                total_db=payment.amount,
                nota_like=nota_like,
            )
            payment.siesa_invoice_number = invoice_number
            payment.siesa_receipt_number = receipt_number

        payment.siesa_response = {
            "invoice": factura_result,
            "receipt": recibo_result,
        }

        logger.info(f"Documentos SIESA completos pago {payment.id}")
