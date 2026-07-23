from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required
from software.models.UsuarioModel import Usuario
import json
from software.utils.autorizaciones import solicitar_autorizacion, validar_codigo_autorizacion

def solicitar_codigo_view(request):
    # Validar sesión personalizada del sistema
    id_usuario_sesion = request.session.get('idusuario')
    if not id_usuario_sesion:
        return JsonResponse({'success': False, 'error': 'Sesión no iniciada'}, status=401)
    
    usuario = Usuario.objects.filter(idusuario=id_usuario_sesion).first()
    if not usuario:
        return JsonResponse({'success': False, 'error': 'Usuario no encontrado'}, status=404)

    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            tipo_accion = data.get('tipo') # EDICION / ELIMINACION
            modulo = data.get('modulo')
            id_registro = data.get('id')
            
            exito, mensaje = solicitar_autorizacion(usuario, tipo_accion, modulo, id_registro)
            
            if exito:
                return JsonResponse({'success': True, 'message': mensaje})
            else:
                return JsonResponse({'success': False, 'error': mensaje})
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
    return JsonResponse({'success': False, 'error': 'Método no permitido'})

def validar_codigo_view(request):
    # Validar sesión personalizada del sistema
    id_usuario_sesion = request.session.get('idusuario')
    if not id_usuario_sesion:
        return JsonResponse({'success': False, 'error': 'Sesión no iniciada'}, status=401)

    usuario = Usuario.objects.filter(idusuario=id_usuario_sesion).first()
    if not usuario:
        return JsonResponse({'success': False, 'error': 'Usuario no encontrado'}, status=404)

    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            codigo = data.get('codigo')
            tipo_accion = data.get('tipo')
            modulo = data.get('modulo')
            id_registro = data.get('id')
            
            exito, mensaje = validar_codigo_autorizacion(usuario, codigo, tipo_accion, modulo, id_registro)
            
            if exito:
                return JsonResponse({'success': True, 'message': mensaje})
            else:
                return JsonResponse({'success': False, 'error': mensaje})
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
    return JsonResponse({'success': False, 'error': 'Método no permitido'})
