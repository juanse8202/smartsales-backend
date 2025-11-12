from django.contrib import admin
from ventas.models import Cart, CartItem, Venta, DetalleVenta, Pago


# ==================== ADMIN PARA CARRITO ====================

class CartItemInline(admin.TabularInline):
    model = CartItem
    extra = 0
    readonly_fields = ['subtotal']


@admin.register(Cart)
class CartAdmin(admin.ModelAdmin):
    list_display = ['id', 'user', 'created_at', 'total_price']
    list_filter = ['created_at']
    search_fields = ['user__username', 'user__email']
    inlines = [CartItemInline]
    readonly_fields = ['id', 'created_at', 'updated_at', 'total_price']


# ==================== ADMIN PARA VENTAS ====================

class DetalleVentaInline(admin.TabularInline):
    model = DetalleVenta
    extra = 1
    readonly_fields = ['subtotal', 'total']
    fields = ['catalogo', 'cantidad', 'precio_unitario', 'descuento', 'subtotal', 'total']


@admin.register(Venta)
class VentaAdmin(admin.ModelAdmin):
    list_display = ['id', 'cliente', 'fecha', 'total', 'estado']
    list_filter = ['estado', 'fecha']
    search_fields = ['cliente__nombre', 'cliente__nit_ci']
    date_hierarchy = 'fecha'
    inlines = [DetalleVentaInline]
    readonly_fields = ['id', 'fecha', 'total']
    fieldsets = (
        ('Información del Cliente', {
            'fields': ('cliente', 'direccion')
        }),
        ('Información de la Venta', {
            'fields': ('fecha', 'estado')
        }),
        ('Detalles Financieros', {
            'fields': ('subtotal', 'impuesto', 'descuento', 'costo_envio', 'total')
        }),
    )


@admin.register(DetalleVenta)
class DetalleVentaAdmin(admin.ModelAdmin):
    list_display = ['id', 'venta', 'catalogo', 'cantidad', 'precio_unitario', 'total']
    list_filter = ['venta__fecha']
    search_fields = ['venta__id', 'catalogo__nombre']
    readonly_fields = ['subtotal', 'total']


# ==================== ADMIN PARA PAGOS ====================

@admin.register(Pago)
class PagoAdmin(admin.ModelAdmin):
    list_display = ['id', 'venta', 'fecha_pago', 'monto', 'moneda', 'estado', 'proveedor']
    list_filter = ['estado', 'moneda', 'fecha_pago', 'proveedor']
    search_fields = ['venta__id', 'transaccion_id', 'proveedor']
    date_hierarchy = 'fecha_pago'
    readonly_fields = ['id', 'fecha_pago']
    fieldsets = (
        ('Información de la Venta', {
            'fields': ('venta',)
        }),
        ('Detalles del Pago', {
            'fields': ('fecha_pago', 'monto', 'moneda', 'estado')
        }),
        ('Información del Proveedor', {
            'fields': ('proveedor', 'transaccion_id')
        }),
    )
