# 📡 Endpoints API - Módulo Finanzas

**Base URL:** `http://localhost:8000/api/finanzas/`

---

## 🔹 Crear Payment Intent

**Endpoint:** `POST /api/finanzas/stripe/create-payment-intent/`

**Body:**
```json
{
  "venta_id": 1,
  "monto": 500.00,
  "moneda": "BOB",
  "descripcion": "Pago de venta"
}
```

**Response:**
```json
{
  "client_secret": "pi_xxx_secret_xxx",
  "payment_intent_id": "pi_xxx",
  "pago_id": 1,
  "monto": 500.0,
  "moneda": "BOB",
  "venta_id": 1
}
```

---

## 🔹 Confirmar Pago Automático (Solo Pruebas)

**Endpoint:** `POST /api/finanzas/stripe/confirm-payment-auto/`

**Body:**
```json
{
  "payment_intent_id": "pi_xxx"
}
```

**Response:**
```json
{
  "success": true,
  "status": "succeeded",
  "payment_intent_id": "pi_xxx",
  "message": "Pago confirmado automáticamente"
}
```

---

## 🔹 Confirmar Pago con Tarjeta

**Endpoint:** `POST /api/finanzas/stripe/confirm-payment-with-card/`

**Body:**
```json
{
  "payment_intent_id": "pi_xxx",
  "payment_method_id": "pm_card_visa"
}
```

O con número de tarjeta:
```json
{
  "payment_intent_id": "pi_xxx",
  "card_number": "4242424242424242"
}
```

**Response:**
```json
{
  "success": true,
  "status": "succeeded",
  "payment_intent_id": "pi_xxx",
  "payment_method_id": "pm_card_visa",
  "message": "Pago procesado exitosamente"
}
```

---

## 🔹 Verificar Estado del Pago

**Endpoint:** `POST /api/finanzas/stripe/verify-payment/`

**Body:**
```json
{
  "payment_intent_id": "pi_xxx"
}
```

**Response:**
```json
{
  "status": "succeeded",
  "venta_id": "1",
  "pago": {
    "id": 1,
    "venta": 1,
    "monto": "500.00",
    "moneda": "BOB",
    "estado": "completado",
    "proveedor": "Stripe",
    "transaccion_id": "pi_xxx",
    "fecha_pago": "2025-11-10T10:30:00Z"
  },
  "message": "Pago en estado: succeeded"
}
```

---

## 🔹 Listar Pagos

**Endpoint:** `GET /api/finanzas/pagos-stripe/`

**Query Params:**
- `venta` - Filtrar por ID de venta
- `estado` - Filtrar por estado (pendiente, completado, fallido, reembolsado)
- `proveedor` - Filtrar por proveedor

**Ejemplos:**
```
GET /api/finanzas/pagos-stripe/
GET /api/finanzas/pagos-stripe/?venta=1
GET /api/finanzas/pagos-stripe/?estado=completado
GET /api/finanzas/pagos-stripe/?proveedor=Stripe
```

**Response:**
```json
[
  {
    "id": 1,
    "venta_id": 1,
    "cliente_nombre": "Juan Pérez",
    "monto": "500.00",
    "moneda": "BOB",
    "estado": "completado",
    "proveedor": "Stripe",
    "fecha_pago": "2025-11-10T10:30:00Z",
    "transaccion_id": "pi_xxx"
  }
]
```

---

## 🔹 Detalle de Pago

**Endpoint:** `GET /api/finanzas/pagos-stripe/{id}/`

**Ejemplo:**
```
GET /api/finanzas/pagos-stripe/1/
```

**Response:**
```json
{
  "id": 1,
  "venta": 1,
  "venta_info": {
    "id": 1,
    "total": 500.0,
    "estado": "completada",
    "fecha": "2025-11-10 10:00:00"
  },
  "cliente_info": {
    "id": 1,
    "nombre": "Juan Pérez",
    "email": "juan@example.com"
  },
  "monto": "500.00",
  "moneda": "BOB",
  "estado": "completado",
  "proveedor": "Stripe",
  "transaccion_id": "pi_xxx",
  "fecha_pago": "2025-11-10T10:30:00Z"
}
```

---

## 💳 Payment Methods de Prueba

```
pm_card_visa          - Visa exitosa
pm_card_mastercard    - Mastercard exitosa
pm_card_amex          - American Express exitosa
```

## 💳 Tarjetas de Prueba

```
4242424242424242      - Visa exitosa
5555555555554444      - Mastercard exitosa
378282246310005       - American Express exitosa
4000000000000002      - Tarjeta rechazada
4000000000009995      - Fondos insuficientes
```

**Para todas:** Fecha de expiración futura (ej: 12/26) y CVV cualquiera (ej: 123)

---

## 📊 Estados de Pago

- `pendiente` - Pago creado pero no confirmado
- `completado` - Pago exitoso
- `fallido` - Pago rechazado
- `reembolsado` - Pago reembolsado

---

## 🔄 Flujo Típico

1. **Crear Payment Intent**: `POST /stripe/create-payment-intent/`
2. **Confirmar Pago**: `POST /stripe/confirm-payment-with-card/`
3. **Verificar Estado**: `POST /stripe/verify-payment/`
4. **Consultar Detalle**: `GET /pagos-stripe/{id}/`

---

## 🚀 Testing Rápido con cURL

```bash
# 1. Crear Payment Intent
curl -X POST http://localhost:8000/api/finanzas/stripe/create-payment-intent/ \
  -H "Content-Type: application/json" \
  -d '{"venta_id": 1}'

# 2. Confirmar automáticamente (copiar payment_intent_id del paso 1)
curl -X POST http://localhost:8000/api/finanzas/stripe/confirm-payment-auto/ \
  -H "Content-Type: application/json" \
  -d '{"payment_intent_id": "pi_xxx"}'

# 3. Verificar
curl -X POST http://localhost:8000/api/finanzas/stripe/verify-payment/ \
  -H "Content-Type: application/json" \
  -d '{"payment_intent_id": "pi_xxx"}'

# 4. Listar todos los pagos
curl http://localhost:8000/api/finanzas/pagos-stripe/
```

---

## 📝 Notas

- Todos los endpoints de consulta (`GET`) requieren autenticación
- Los endpoints de creación/confirmación (`POST`) son públicos para facilitar pruebas
- El pago se registra automáticamente en la tabla `ventas_pago`
- Al completar un pago, la venta se marca como `completada` automáticamente
