#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.infra.config.database import SessionLocal
from src.domain.entities.payment import Payment
from src.app.use_cases.payment_use_cases import PaymentUseCases


def generar_documentos_siesa_para_pago(payment_id):
    db = SessionLocal()
    try:
        payment = db.get(Payment, payment_id)

        if not payment:
            print(f"\n❌ ERROR: Pago {payment_id} no encontrado\n")
            return False

        if payment.status != "APPROVED":
            print(f"\n❌ ERROR: Pago {payment_id} no está aprobado")
            print(f"   Estado actual: {payment.status}\n")
            return False

        if payment.order.status != "PAID":
            print(f"\n⚠️  ADVERTENCIA: Orden {payment.order.id} no está en estado PAID")
            print(f"   Estado actual: {payment.order.status}\n")

        print("\n" + "=" * 70)
        print("📋 INFORMACIÓN DEL PAGO")
        print("=" * 70)
        print(f"  Payment ID:        {payment.id}")
        print(f"  Orden ID:          {payment.order.id}")
        print(f"  Monto:             ${payment.amount:,.2f}")
        print(f"  Estado:            {payment.status}")
        print(f"  Factura SIESA:     {payment.siesa_invoice_number or 'Pendiente'}")
        print(f"  Recibo SIESA:      {payment.siesa_receipt_number or 'Pendiente'}")
        print("=" * 70)

        if payment.siesa_invoice_number or payment.siesa_receipt_number:
            print("\n⚠️  ADVERTENCIA: Este pago ya tiene documentos SIESA generados")
            respuesta = input("\n¿Desea continuar de todas formas? (si/no): ")
            if respuesta.lower() not in ['si', 's', 'yes', 'y']:
                print("\n❌ Operación cancelada por el usuario\n")
                return False

        try:
            print("\n🚀 Generando documentos SIESA...\n")
            PaymentUseCases(db)._generar_documentos_siesa(payment)

            print("\n" + "=" * 70)
            print("✅ DOCUMENTOS SIESA GENERADOS EXITOSAMENTE")
            print("=" * 70)
            print(f"  Factura SIESA:     {payment.siesa_invoice_number}")
            print(f"  Recibo SIESA:      {payment.siesa_receipt_number}")
            print("=" * 70 + "\n")

            payment.siesa_error = None
            return True

        except Exception as e:
            print("\n" + "=" * 70)
            print("❌ ERROR AL GENERAR DOCUMENTOS SIESA")
            print("=" * 70)
            print(f"  Error: {str(e)}")
            print(f"\n  El error ha sido guardado en payment.siesa_error")
            print("=" * 70 + "\n")
            payment.siesa_error = str(e)
            return False

        finally:
            db.commit()

    finally:
        db.close()


def main():
    if len(sys.argv) < 2:
        print("\n" + "=" * 70)
        print("📝 USO DEL SCRIPT")
        print("=" * 70)
        print("  python call_siesa.py <payment_id>")
        print("=" * 70 + "\n")
        sys.exit(1)

    try:
        payment_id = int(sys.argv[1])
    except ValueError:
        print("\n❌ ERROR: El payment_id debe ser un número entero\n")
        sys.exit(1)

    success = generar_documentos_siesa_para_pago(payment_id)
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()