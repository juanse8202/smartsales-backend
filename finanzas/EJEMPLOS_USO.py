"""
Ejemplos de uso del módulo de Finanzas con Stripe

Este archivo contiene ejemplos de cómo usar los endpoints de pago con Stripe
"""

# ============================================
# EJEMPLO 1: Crear y Confirmar Pago Automático
# ============================================

import requests

BASE_URL = "http://localhost:8000/api/finanzas"

# Paso 1: Crear una venta (asumiendo que ya existe venta_id=1)
venta_id = 1

# Paso 2: Crear Payment Intent
response = requests.post(f"{BASE_URL}/stripe/create-payment-intent/", json={
    "venta_id": venta_id,
    "monto": 500.00,  # Opcional, usa el total de la venta por defecto
    "moneda": "BOB",
    "descripcion": "Pago de venta de prueba"
})

data = response.json()
print("✅ Payment Intent creado:")
print(f"   - Payment Intent ID: {data['payment_intent_id']}")
print(f"   - Client Secret: {data['client_secret']}")
print(f"   - Pago ID: {data['pago_id']}")

payment_intent_id = data['payment_intent_id']

# Paso 3: Confirmar pago automáticamente (SOLO PARA PRUEBAS)
response = requests.post(f"{BASE_URL}/stripe/confirm-payment-auto/", json={
    "payment_intent_id": payment_intent_id
})

print("\n✅ Pago confirmado:")
print(response.json())

# Paso 4: Verificar el estado del pago
response = requests.post(f"{BASE_URL}/stripe/verify-payment/", json={
    "payment_intent_id": payment_intent_id
})

print("\n✅ Estado del pago:")
print(response.json())


# ============================================
# EJEMPLO 2: Confirmar Pago con Tarjeta Específica
# ============================================

# Paso 1: Crear Payment Intent (igual que el ejemplo 1)
response = requests.post(f"{BASE_URL}/stripe/create-payment-intent/", json={
    "venta_id": 2,
    "moneda": "USD"
})
payment_intent_id = response.json()['payment_intent_id']

# Paso 2: Confirmar con Payment Method específico
response = requests.post(f"{BASE_URL}/stripe/confirm-payment-with-card/", json={
    "payment_intent_id": payment_intent_id,
    "payment_method_id": "pm_card_visa"  # Visa de prueba
})

print("\n✅ Pago con tarjeta:")
print(response.json())


# ============================================
# EJEMPLO 3: Confirmar Pago con Número de Tarjeta
# ============================================

# Paso 1: Crear Payment Intent
response = requests.post(f"{BASE_URL}/stripe/create-payment-intent/", json={
    "venta_id": 3
})
payment_intent_id = response.json()['payment_intent_id']

# Paso 2: Confirmar con número de tarjeta de prueba
response = requests.post(f"{BASE_URL}/stripe/confirm-payment-with-card/", json={
    "payment_intent_id": payment_intent_id,
    "card_number": "4242424242424242"  # Visa de prueba
})

print("\n✅ Pago con número de tarjeta:")
print(response.json())


# ============================================
# EJEMPLO 4: Listar Pagos
# ============================================

# Listar todos los pagos
response = requests.get(f"{BASE_URL}/pagos-stripe/")
print("\n✅ Lista de pagos:")
for pago in response.json():
    print(f"   - Pago #{pago['id']}: {pago['moneda']} {pago['monto']} - {pago['estado']}")

# Filtrar por venta
response = requests.get(f"{BASE_URL}/pagos-stripe/?venta=1")
print("\n✅ Pagos de la venta #1:")
print(response.json())

# Filtrar por estado
response = requests.get(f"{BASE_URL}/pagos-stripe/?estado=completado")
print("\n✅ Pagos completados:")
print(response.json())


# ============================================
# EJEMPLO 5: Detalle de un Pago
# ============================================

pago_id = 1
response = requests.get(f"{BASE_URL}/pagos-stripe/{pago_id}/")
print(f"\n✅ Detalle del pago #{pago_id}:")
print(response.json())


# ============================================
# EJEMPLO 6: Flujo Frontend (JavaScript/React)
# ============================================

"""
// En el frontend (React/JavaScript):

// 1. Crear Payment Intent
const createPayment = async (ventaId) => {
  const response = await fetch('http://localhost:8000/api/finanzas/stripe/create-payment-intent/', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ venta_id: ventaId })
  });
  
  const data = await response.json();
  return data;
};

// 2. Configurar Stripe Elements
import { loadStripe } from '@stripe/stripe-js';
import { CardElement, Elements, useStripe, useElements } from '@stripe/react-stripe-js';

const stripePromise = loadStripe('pk_test_tu_clave_publica');

const CheckoutForm = ({ clientSecret, paymentIntentId }) => {
  const stripe = useStripe();
  const elements = useElements();
  
  const handleSubmit = async (event) => {
    event.preventDefault();
    
    if (!stripe || !elements) return;
    
    // Confirmar el pago con Stripe
    const { paymentIntent, error } = await stripe.confirmCardPayment(clientSecret, {
      payment_method: {
        card: elements.getElement(CardElement),
        billing_details: {
          name: 'Cliente'
        }
      }
    });
    
    if (error) {
      console.error('Error:', error.message);
      return;
    }
    
    // Verificar el pago en el backend
    const response = await fetch('http://localhost:8000/api/finanzas/stripe/verify-payment/', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ payment_intent_id: paymentIntent.id })
    });
    
    const data = await response.json();
    console.log('Pago confirmado:', data);
  };
  
  return (
    <form onSubmit={handleSubmit}>
      <CardElement />
      <button type="submit" disabled={!stripe}>
        Pagar
      </button>
    </form>
  );
};

// 3. Usar el componente
const App = () => {
  const [clientSecret, setClientSecret] = useState(null);
  const [paymentIntentId, setPaymentIntentId] = useState(null);
  
  useEffect(() => {
    // Crear Payment Intent cuando se carga el componente
    createPayment(1).then(data => {
      setClientSecret(data.client_secret);
      setPaymentIntentId(data.payment_intent_id);
    });
  }, []);
  
  return (
    <Elements stripe={stripePromise}>
      {clientSecret && (
        <CheckoutForm 
          clientSecret={clientSecret} 
          paymentIntentId={paymentIntentId}
        />
      )}
    </Elements>
  );
};
"""


# ============================================
# TARJETAS DE PRUEBA
# ============================================

"""
Números de tarjeta de prueba:

ÉXITO:
- 4242424242424242 - Visa
- 5555555555554444 - Mastercard
- 378282246310005 - American Express

RECHAZADAS:
- 4000000000000002 - Tarjeta rechazada
- 4000000000009995 - Fondos insuficientes
- 4000000000009987 - CVV incorrecto

Payment Methods de prueba:
- pm_card_visa - Visa exitosa
- pm_card_mastercard - Mastercard exitosa
- pm_card_amex - American Express exitosa

Para todos: Usa cualquier fecha futura (ej: 12/26) y cualquier CVV de 3 dígitos (ej: 123)
"""


# ============================================
# TESTING CON CURL
# ============================================

"""
# Crear Payment Intent
curl -X POST http://localhost:8000/api/finanzas/stripe/create-payment-intent/ \
  -H "Content-Type: application/json" \
  -d '{"venta_id": 1, "monto": 500.00, "moneda": "BOB"}'

# Confirmar pago automático
curl -X POST http://localhost:8000/api/finanzas/stripe/confirm-payment-auto/ \
  -H "Content-Type: application/json" \
  -d '{"payment_intent_id": "pi_xxx"}'

# Verificar pago
curl -X POST http://localhost:8000/api/finanzas/stripe/verify-payment/ \
  -H "Content-Type: application/json" \
  -d '{"payment_intent_id": "pi_xxx"}'

# Listar pagos
curl http://localhost:8000/api/finanzas/pagos-stripe/

# Detalle de pago
curl http://localhost:8000/api/finanzas/pagos-stripe/1/
"""
