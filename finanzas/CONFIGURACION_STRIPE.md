# 🔑 Configuración de Claves de Stripe

## Paso 1: Crear Cuenta en Stripe

1. Ve a [https://dashboard.stripe.com/register](https://dashboard.stripe.com/register)
2. Regístrate con tu email
3. Completa la información básica

## Paso 2: Obtener Claves de Prueba

1. Una vez dentro del dashboard, ve a **Developers → API Keys**
2. Asegúrate de estar en **modo de prueba** (Test mode) - Hay un switch en la parte superior derecha
3. Verás dos claves:
   - **Publishable key** (Clave pública) - Comienza con `pk_test_...`
   - **Secret key** (Clave secreta) - Comienza con `sk_test_...`

## Paso 3: Configurar en tu Proyecto

### Opción A: Usar archivo .env (Recomendado)

Crea o edita el archivo `.env` en la raíz del proyecto:

```bash
# Stripe API Keys
STRIPE_SECRET_KEY=sk_test_tu_clave_secreta_copiada_aqui
STRIPE_PUBLISHABLE_KEY=pk_test_tu_clave_publica_copiada_aqui
```

### Opción B: Configurar directamente en settings.py (No recomendado para producción)

Edita `SmartSales365/settings.py`:

```python
# Al final del archivo
STRIPE_SECRET_KEY = 'sk_test_tu_clave_secreta'
STRIPE_PUBLISHABLE_KEY = 'pk_test_tu_clave_publica'
```

## Paso 4: Verificar Configuración

Ejecuta:

```bash
python manage.py shell
```

Luego dentro del shell:

```python
from django.conf import settings
print(settings.STRIPE_SECRET_KEY)
print(settings.STRIPE_PUBLISHABLE_KEY)
```

Si ves tus claves (que comiencen con `sk_test_` y `pk_test_`), ¡está configurado correctamente!

## Paso 5: Probar la Integración

Crea un Payment Intent de prueba:

```bash
# Asegúrate de tener el servidor corriendo
python manage.py runserver

# En otra terminal, prueba crear un pago:
curl -X POST http://localhost:8000/api/finanzas/stripe/create-payment-intent/ \
  -H "Content-Type: application/json" \
  -d '{"venta_id": 1, "monto": 100.00}'
```

## 🔒 Seguridad

### ❌ NUNCA HAGAS ESTO:

- ✗ Compartir tu `STRIPE_SECRET_KEY` en GitHub o repositorios públicos
- ✗ Usar la clave secreta en el frontend
- ✗ Commitear el archivo `.env` al repositorio

### ✅ BUENAS PRÁCTICAS:

- ✓ Agrega `.env` a tu `.gitignore`
- ✓ Solo usa `STRIPE_PUBLISHABLE_KEY` en el frontend
- ✓ Mantén `STRIPE_SECRET_KEY` solo en el backend
- ✓ Usa claves de prueba (`sk_test_` / `pk_test_`) durante desarrollo
- ✓ Usa claves de producción (`sk_live_` / `pk_live_`) solo en producción

## 📝 Archivo .gitignore

Asegúrate de que tu `.gitignore` incluya:

```
.env
*.env
.env.local
```

## 🆘 Problemas Comunes

### "Invalid API Key provided"
- Verifica que copiaste la clave completa sin espacios
- Asegúrate de estar usando las claves correctas (test vs live)

### "No API key provided"
- Verifica que el archivo `.env` está en la raíz del proyecto
- Reinicia el servidor después de agregar las claves

### Las claves no se cargan
- Asegúrate de tener instalado `python-decouple`:
  ```bash
  pip install python-decouple
  ```
- Verifica que estás usando `config()` en settings.py

## 🎓 Para Proyecto Universitario

Para tu proyecto universitario, puedes usar las claves de prueba sin problema. Stripe te da acceso completo a todas las funcionalidades en modo de prueba.

**Claves de prueba predeterminadas del ejemplo** (puedes usarlas temporalmente):
```
STRIPE_SECRET_KEY=sk_test_51QQkQMITLTTvpAjcEK...
STRIPE_PUBLISHABLE_KEY=pk_test_51QQkQMITLTTvpAjcEK...
```

Pero es mejor que crees tu propia cuenta para tener acceso al dashboard completo.

## 📚 Recursos Útiles

- [Dashboard de Stripe](https://dashboard.stripe.com/)
- [Documentación de API Keys](https://stripe.com/docs/keys)
- [Modo de Prueba](https://stripe.com/docs/testing)
- [Tarjetas de Prueba](https://stripe.com/docs/testing#cards)

## ✅ Checklist Final

- [ ] Cuenta de Stripe creada
- [ ] Modo de prueba activado
- [ ] Claves copiadas desde el dashboard
- [ ] Archivo `.env` creado y configurado
- [ ] `.env` agregado a `.gitignore`
- [ ] Servidor reiniciado
- [ ] Configuración verificada con `python manage.py shell`
- [ ] Primer pago de prueba exitoso

¡Listo! Ahora puedes usar Stripe en tu proyecto. 🎉
