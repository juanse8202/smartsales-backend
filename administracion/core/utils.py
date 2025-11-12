from ..models import RegistroBitacora

def get_client_ip(request):
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip

def registrar_bitacora(request, usuario, accion, descripcion, modulo=None):
    try:
        ip = get_client_ip(request)
        usuario_a_registrar = None
        if usuario and usuario.is_authenticated:
            usuario_a_registrar = usuario
        
        RegistroBitacora.objects.create(
            usuario=usuario_a_registrar,
            accion=accion,
            descripcion=descripcion,
            modulo=modulo,
            ip_address=ip
        )
    except Exception as e:
        print(f'Error al registrar en la bitácora: {e}')
