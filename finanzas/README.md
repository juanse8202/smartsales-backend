# Módulo de Finanzas - Integración con Stripe

Este módulo gestiona los pagos de ventas utilizando Stripe como proveedor de pagos.

## 🚀 Configuración Inicial

### 1. Instalar Stripe

```bash
pip install stripe==11.1.1
```

### 2. Configurar Variables de Entorno

Agrega las siguientes variables en tu archivo `.env`:

```bash
# Stripe API Keys (obtener en https://dashboard.stripe.com/test/apikeys)
STRIPE_SECRET_KEY=sk_test_tu_clave_secreta_aqui
STRIPE_PUBLISHABLE_KEY=pk_test_tu_clave_publica_aqui
```

### 3. Obtener Claves de Stripe

1. Crea una cuenta en [Stripe](https://dashboard.stripe.com/register)
2. Ve a **Developers → API Keys**
3. Copia la **Secret Key** (sk_test_...) y **Publishable Key** (pk_test_...)
4. Pégalas en tu archivo `.env`

### 4. Aplicar Migraciones

```bash
python manage.py makemigrations
python manage.py migrate
```

### 5. Verificar Instalación

```bash
python manage.py check
```

## 📋 Endpoints Disponibles

### Base URL: `/api/finanzas/`

### 1. Crear Payment Intent
**POST** `/api/finanzas/stripe/create-payment-intent/`

Crea un Payment Intent en Stripe y registra el pago en la BD.

**Request Body:**
```json
{
  "venta_id": 1,
  "monto": 500.00,  // Opcional, usa el total de la venta por defecto
  "moneda": "BOB",  // Opcional: BOB, USD, EUR
  "descripcion": "Pago de venta #1"  // Opcional
}
```

**Response:**
```json
{
  "client_secret": "pi_xxx_secret_xxx",
  "payment_intent_id": "pi_xxx",
  "pago_id": 1,
  "monto": 500.00,
  "moneda": "BOB",
  "venta_id": 1
}
```

### 2. Confirmar Pago Automático (SOLO PRUEBAS)
**POST** `/api/finanzas/stripe/confirm-payment-auto/`

Confirma automáticamente un pago usando tarjeta de prueba.

**Request Body:**
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

### 3. Confirmar Pago con Tarjeta
**POST** `/api/finanzas/stripe/confirm-payment-with-card/`

Confirma un pago con un Payment Method específico.

**Request Body:**
```json
{
  "payment_intent_id": "pi_xxx",
  "payment_method_id": "pm_card_visa"  // O usar card_number: "4242424242424242"
}
```

**Payment Methods de Prueba:**
- `pm_card_visa` - Visa exitosa
- `pm_card_mastercard` - Mastercard exitosa
- `pm_card_amex` - American Express exitosa

**Tarjetas de Prueba:**
- `4242424242424242` - Visa exitosa
- `5555555555554444` - Mastercard exitosa
- `378282246310005` - American Express exitosa

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

### 4. Verificar Estado del Pago
**POST** `/api/finanzas/stripe/verify-payment/`

Verifica el estado de un Payment Intent y actualiza la BD.

**Request Body:**
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

### 5. Listar Pagos
**GET** `/api/finanzas/pagos-stripe/`

Lista todos los pagos con filtros opcionales.

**Query Params:**
- `venta` - Filtrar por ID de venta
- `estado` - Filtrar por estado (pendiente, completado, fallido, reembolsado)
- `proveedor` - Filtrar por proveedor

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

### 6. Detalle de Pago
**GET** `/api/finanzas/pagos-stripe/{id}/`

Obtiene los detalles completos de un pago.

**Response:**
```json
{
  "id": 1,
  "venta": 1,
  "venta_info": {
    "id": 1,
    "total": 500.00,
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

## 🔄 Flujo de Pago Completo

### Opción 1: Pago Manual (Para Testing)

```python
# 1. Crear Payment Intent
response = requests.post('http://localhost:8000/api/finanzas/stripe/create-payment-intent/', json={
    "venta_id": 1,
    "monto": 500.00,
    "moneda": "BOB"
})
data = response.json()
payment_intent_id = data['payment_intent_id']

# 2. Confirmar pago automáticamente (SOLO PRUEBAS)
response = requests.post('http://localhost:8000/api/finanzas/stripe/confirm-payment-auto/', json={
    "payment_intent_id": payment_intent_id
})

# 3. Verificar el pago
response = requests.post('http://localhost:8000/api/finanzas/stripe/verify-payment/', json={
    "payment_intent_id": payment_intent_id
})
```

### Opción 2: Flujo con Frontend (Stripe Elements)

```javascript
// 1. Crear Payment Intent desde el backend
const response = await fetch('/api/finanzas/stripe/create-payment-intent/', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({ venta_id: 1 })
});
const { client_secret } = await response.json();

// 2. Usar Stripe Elements en el frontend para capturar tarjeta
const stripe = Stripe('pk_test_tu_clave_publica');
const { paymentIntent, error } = await stripe.confirmCardPayment(client_secret, {
  payment_method: {
    card: cardElement,
    billing_details: { name: 'Cliente' }
  }
});

// 3. Verificar el pago en el backend
await fetch('/api/finanzas/stripe/verify-payment/', {
  method: 'POST',
  body: JSON.stringify({ payment_intent_id: paymentIntent.id })
});
```

## 🧪 Testing

### Tarjetas de Prueba

| Número | Marca | Resultado |
|--------|-------|-----------|
| 4242424242424242 | Visa | Pago exitoso |
| 5555555555554444 | Mastercard | Pago exitoso |
| 378282246310005 | American Express | Pago exitoso |
| 4000000000000002 | Visa | Tarjeta rechazada |
| 4000000000009995 | Visa | Fondos insuficientes |

**Fecha de expiración:** Cualquier fecha futura (ej: 12/26)  
**CVV:** Cualquier 3 dígitos (ej: 123)

### Payment Methods de Prueba

```
pm_card_visa - Visa exitosa
pm_card_mastercard - Mastercard exitosa
pm_card_amex - American Express exitosa
pm_card_visa_chargeDispute - Disputa de cargo
pm_card_visa_debit - Visa débito
```

## 📊 Estados de Pago

- **pendiente**: Pago creado pero no confirmado
- **completado**: Pago exitoso
- **fallido**: Pago rechazado
- **reembolsado**: Pago reembolsado

## 🔒 Seguridad

- ⚠️ **NUNCA** expongas tu `STRIPE_SECRET_KEY` en el frontend
- ✅ Usa `STRIPE_PUBLISHABLE_KEY` en el frontend
- ✅ Todas las operaciones sensibles se hacen en el backend
- ✅ Valida siempre el estado del pago en el backend después de confirmar

## 📝 Notas

- Este módulo usa Stripe API v13+
- Los pagos se registran en el modelo `Pago` existente en `ventas/models/models_venta.py`
- Al completar un pago, se actualiza automáticamente el estado de la venta a `completada`
- Para producción, reemplaza las claves de prueba por claves reales

## 🆘 Solución de Problemas

### Error: "No module named 'stripe'"
```bash
pip install stripe==11.1.1
```

### Error: "STRIPE_SECRET_KEY not configured"
Agrega las claves en tu archivo `.env`

### Error: "Invalid API Key"
Verifica que copiaste correctamente las claves desde el dashboard de Stripe

### Pago no se actualiza en BD
Llama al endpoint `/api/finanzas/stripe/verify-payment/` después de confirmar

## 📚 Recursos

- [Documentación de Stripe](https://stripe.com/docs)
- [Stripe Dashboard](https://dashboard.stripe.com/)
- [Stripe Testing](https://stripe.com/docs/testing)
