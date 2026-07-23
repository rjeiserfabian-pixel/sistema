from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse, HttpResponse
from software.models.TipoCuentaModel import TipoCuenta
from software.models.CanalPagoModel import CanalPago
from software.models.detalletipousuarioxmodulosModel import Detalletipousuarioxmodulos

def canales_pago_view(request):
    """
    Vista principal para renderizar el template de Canales de Pago.
    """
    id2 = request.session.get('idtipousuario')
    if not id2:
        return HttpResponse("<h1>No tiene acceso. Por favor inicie sesión.</h1>")
    
    return render(request, 'gestion/canales_pago.html')

# ==========================================
# CRUD TIPO DE CUENTA
# ==========================================

def listar_tipos_cuenta(request):
    tipos = TipoCuenta.objects.all().order_by('id_tipo_cuenta')
    data = []
    for t in tipos:
        data.append({
            'id_tipo_cuenta': t.id_tipo_cuenta,
            'nombre': t.nombre,
            'estado': t.estado
        })
    return JsonResponse({'data': data})

def guardar_tipo_cuenta(request):
    if request.method == 'POST':
        try:
            id_tipo_cuenta = request.POST.get('id_tipo_cuenta')
            nombre = request.POST.get('nombre')
            estado = request.POST.get('estado') == 'true'

            if id_tipo_cuenta:
                tipo = TipoCuenta.objects.get(id_tipo_cuenta=id_tipo_cuenta)
                tipo.nombre = nombre
                tipo.estado = estado
                tipo.save()
                mensaje = "Tipo de cuenta actualizado correctamente"
            else:
                TipoCuenta.objects.create(
                    nombre=nombre,
                    estado=estado
                )
                mensaje = "Tipo de cuenta creado correctamente"

            return JsonResponse({'ok': True, 'success': True, 'mensaje': mensaje})
        except Exception as e:
            return JsonResponse({'ok': False, 'success': False, 'error': str(e)})
    return JsonResponse({'ok': False, 'success': False, 'error': 'Método no permitido'})

def eliminar_tipo_cuenta(request):
    if request.method == 'POST':
        try:
            id_tipo_cuenta = request.POST.get('id_tipo_cuenta')
            # Lógica de eliminación (en este caso lo pasamos a estado inactivo para evitar conflictos FK)
            tipo = TipoCuenta.objects.get(id_tipo_cuenta=id_tipo_cuenta)
            tipo.estado = False
            tipo.save()
            return JsonResponse({'ok': True, 'success': True, 'mensaje': 'Tipo de cuenta desactivado'})
        except Exception as e:
            return JsonResponse({'ok': False, 'success': False, 'error': str(e)})
    return JsonResponse({'ok': False, 'success': False, 'error': 'Método no permitido'})

# ==========================================
# CRUD CANALES DE PAGO
# ==========================================

def listar_canales_pago(request):
    canales = CanalPago.objects.select_related('id_tipo_cuenta').all().order_by('orden', 'banco')
    data = []
    for c in canales:
        data.append({
            'id_canal': c.id_canal,
            'banco': c.banco,
            'id_tipo_cuenta': c.id_tipo_cuenta.id_tipo_cuenta if c.id_tipo_cuenta else None,
            'tipo_cuenta_nombre': c.id_tipo_cuenta.nombre if c.id_tipo_cuenta else '',
            'numero_cuenta': c.numero_cuenta,
            'cci': c.cci or '',
            'codigo_agente': c.codigo_agente or '',
            'titular': c.titular or '',
            'orden': c.orden,
            'estado': c.estado
        })
    return JsonResponse({'data': data})

def guardar_canal_pago(request):
    if request.method == 'POST':
        try:
            id_canal = request.POST.get('id_canal')
            banco = request.POST.get('banco')
            id_tipo_cuenta = request.POST.get('id_tipo_cuenta')
            numero_cuenta = request.POST.get('numero_cuenta')
            cci = request.POST.get('cci')
            codigo_agente = request.POST.get('codigo_agente')
            titular = request.POST.get('titular')
            orden = int(request.POST.get('orden', 0))
            estado = request.POST.get('estado') == 'true'

            tipo_cuenta = TipoCuenta.objects.get(id_tipo_cuenta=id_tipo_cuenta)

            if id_canal:
                canal = CanalPago.objects.get(id_canal=id_canal)
                canal.banco = banco
                canal.id_tipo_cuenta = tipo_cuenta
                canal.numero_cuenta = numero_cuenta
                canal.cci = cci
                canal.codigo_agente = codigo_agente
                canal.titular = titular
                canal.orden = orden
                canal.estado = estado
                canal.save()
                mensaje = "Canal de pago actualizado correctamente"
            else:
                CanalPago.objects.create(
                    banco=banco,
                    id_tipo_cuenta=tipo_cuenta,
                    numero_cuenta=numero_cuenta,
                    cci=cci,
                    codigo_agente=codigo_agente,
                    titular=titular,
                    orden=orden,
                    estado=estado
                )
                mensaje = "Canal de pago creado correctamente"

            return JsonResponse({'ok': True, 'success': True, 'mensaje': mensaje})
        except Exception as e:
            return JsonResponse({'ok': False, 'success': False, 'error': str(e)})
    return JsonResponse({'ok': False, 'success': False, 'error': 'Método no permitido'})

def eliminar_canal_pago(request):
    if request.method == 'POST':
        try:
            id_canal = request.POST.get('id_canal')
            canal = CanalPago.objects.get(id_canal=id_canal)
            canal.estado = False
            canal.save()
            return JsonResponse({'ok': True, 'success': True, 'mensaje': 'Canal de pago desactivado'})
        except Exception as e:
            return JsonResponse({'ok': False, 'success': False, 'error': str(e)})
    return JsonResponse({'ok': False, 'success': False, 'error': 'Método no permitido'})
