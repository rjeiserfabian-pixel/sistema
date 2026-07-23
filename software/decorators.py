# software/decorators.py

from functools import wraps
from django.http import JsonResponse
from django.shortcuts import redirect, render
from software.models.AperturaCierreCajaModel import AperturaCierreCaja

def requiere_caja_aperturada(view_func):
    """
    Decorador que verifica si el usuario tiene una caja aperturada antes de realizar ventas/compras
    """
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        idusuario = request.session.get('idusuario')
        
        if not idusuario:
            return redirect('index')
        
        # Verificar si tiene apertura activa
        apertura = AperturaCierreCaja.objects.filter(
            idusuario_id=idusuario,
            estado__in=['abierta', 'reabierta']
        ).first()
        
        if not apertura:
            # No tiene caja abierta
            
            # Si es una petición AJAX (POST para guardar venta/compra)
            if request.method == 'POST':
                if request.POST.get('afecta_caja') == '0':
                    pass
                else:
                    return JsonResponse({
                        'ok': False,
                        'error': 'Debe aperturar una caja antes de realizar esta operación',
                        'necesita_aperturar': True,
                        'codigo': 'CAJA_REQUERIDA'
                    }, status=400)
            
            # Si es una petición GET (mostrar formulario)
            # Permitir ver el formulario pero mostrará alerta al intentar guardar
            pass
        
        # Si tiene caja abierta, guardar en sesión si no está
        if apertura and not request.session.get('id_caja'):
            request.session['id_caja'] = apertura.id_caja.id_caja
            if apertura.id_caja.id_sucursal:
                request.session['id_sucursal'] = apertura.id_caja.id_sucursal.id_sucursal
        
        # Todo OK, ejecutar la vista
        return view_func(request, *args, **kwargs)
    
    return wrapper