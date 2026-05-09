# TCS Camp 2026 — Pendientes manuales antes de salir a producción

---

## 1. Ejecutar migraciones SQL (en orden)

Conéctate a `[EventosTCS_dev]` y ejecuta en este orden:

```
migrations/01_camp_weeks.sql
migrations/02_camp_packages.sql
migrations/03_order_camp_enrollments.sql
```

Son seguros: usan `IF NOT EXISTS` y no tocan tablas existentes.

---

## 2. Crear el evento Camp desde Swagger

Una vez ejecutadas las migraciones, abre Swagger (`/docs`) y sigue este orden:

### 2.1 Crear el evento principal

**`POST /api/events/new`** — requiere el header `x-support-key`.

```json
{
  "title": "TCS CAMP Summer Fun",
  "date": "2026-06-16T08:00:00",
  "location": "Medellin",
  "ticket_price": 0,
  "staff_price": 0,
  "combo_price": 0,
  "description": "Campamento de verano TCS 2026",
  "stock": 9999,
  "is_active": true
}
```

> `ticket_price`, `staff_price` y `combo_price` se dejan en 0 porque Camp
> no usa estos precios; el pricing real está en `camp_weeks` y `camp_packages`.
> `stock` en 9999 porque Camp no usa el stock global de events (lo controla
> por semana). Anota el `id` que devuelva la respuesta — lo necesitas abajo.

---

### 2.2 Insertar las semanas directamente en BD

Swagger no expone un endpoint de creación de semanas aún (está pendiente
para fase posterior). Ejecuta este INSERT en SQL Server reemplazando
`{EVENT_ID}` con el `id` devuelto en el paso anterior:

```sql
INSERT INTO [EventosTCS_dev].[dbo].[camp_weeks]
  (event_id, week_number, label, start_date, end_date, days, price, stock, is_active)
VALUES
  (3, 1, 'Semana 1 — 16 al 19 de junio', '2026-06-16', '2026-06-19', 4, 640000,  999, 1),
  (3, 2, 'Semana 2 — 22 al 26 de junio', '2026-06-22', '2026-06-26', 5, 800000,  999, 1),
  (3, 3, 'Semana 3 — 30 jun al 3 jul',   '2026-06-30', '2026-07-03', 4, 640000,  999, 1);
```

Anota los `id` generados (IDENTITY) — los necesitas para los paquetes.

---

### 2.3 Insertar los paquetes directamente en BD

Reemplaza `{EVENT_ID}` y los IDs de semana (`{W1}`, `{W2}`, `{W3}`)
con los valores reales:

```sql
INSERT INTO [EventosTCS_dev].[dbo].[camp_packages]
  (event_id, code, label, price, week_ids, is_active)
VALUES
  (3, 'PKG_S1S2', 'Paquete A — Semana 1 + Semana 2 (9 días)',     1370000, '1,2',     1),
  (3, 'PKG_S1S3', 'Paquete B — Semana 1 + Semana 3 (8 días)',     1216000, '1,3',     1),
  (3, 'PKG_3S',   'Paquete C — 3 semanas: S1 + S2 + S3 (13 días)',1875000, '1,2,3',1),
  (3, 'DAY',      'Día individual (sujeto a disponibilidad)',       200000,  NULL,            1);
```

---

### 2.4 Verificar desde Swagger

- **`GET /api/events/{event_id}/camp/weeks`** → debe listar las 3 semanas con su stock.
- **`GET /api/events/{event_id}/camp/packages`** → debe listar los 4 paquetes/día.
- **`GET /api/events/{event_id}`** → confirma que el evento está activo.

---

## 3. ⚠️ Agregar entrada SIESA para el evento Camp

**Bloquea la generación de facturas y recibos si no se hace.**

Cuando el equipo de SIESA confirme el `school_services.id` para TCS Camp,
edita este archivo:

```
src/infra/adapters/siesa_adapter.py
```

Busca `EVENT_SERVICE_MAP` y agrega la entrada:

```python
EVENT_SERVICE_MAP = {
    1: 340,
    2: 443,
    {EVENT_ID}: {SERVICE_ID_CAMP},   # ← agregar esto
}
```

Reemplaza `{EVENT_ID}` con el ID del evento creado en el paso 2.1
y `{SERVICE_ID_CAMP}` con el ID que provea SIESA.

---

## 4. ⚠️ Variables de entorno `.env` — perfil Camp

Agregar al `.env` las siguientes 6 variables antes del primer deploy:

```env
# ---------- Perfil CAMP (TCS Camp 2026) ----------
MAIL_USERNAME_CAMP=
MAIL_PASSWORD_CAMP=
MAIL_DEFAULT_SENDER_CAMP=
COMPANY_LOGO_URL_CAMP=
COMPANY_LOGO_FILE_CAMP=logos_camp.png
CAMP_DAY_PRICE=200000
```

> Si el Camp usa las mismas credenciales SMTP que ATTENDEES,
> copia los valores de `MAIL_USERNAME_ATTENDEES` y `MAIL_PASSWORD_ATTENDEES`.
> Las variables deben existir igual aunque sean iguales.

Coloca el archivo del logo en `static/logos_camp.png` (o ajusta
`COMPANY_LOGO_FILE_CAMP` con el nombre real del archivo).

---

## Resumen de pendientes

| # | Acción                                                                | Responsable       | Estado |
| - | ---------------------------------------------------------------------- | ----------------- | ------ |
| 1 | Ejecutar 3 migraciones SQL                                             | Backend           | ⬜     |
| 2 | Crear evento Camp en Swagger (`POST /api/events/new`)                | Backend           | ⬜     |
| 3 | INSERT semanas en `camp_weeks`                                       | Backend           | ⬜     |
| 4 | INSERT paquetes en `camp_packages`                                   | Backend           | ⬜     |
| 5 | Verificar endpoints `/camp/weeks` y `/camp/packages`               | Backend           | ⬜     |
| 6 | Recibir `school_services.id` de SIESA y editar `EVENT_SERVICE_MAP` | Backend + SIESA   | ⬜     |
| 7 | Agregar 6 variables de entorno Camp al `.env`                        | Backend / DevOps  | ⬜     |
| 8 | Copiar logo Camp a `static/logos_camp.png`                           | Backend / Diseño | ⬜     |
