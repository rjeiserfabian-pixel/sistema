from django.utils import timezone
from datetime import timedelta
from software.models.AutorizacionModel import AutorizacionAccion
from software.models.empresaModel import Empresa
from software.utils.whatsapp_utils import enviar_whatsapp_ultramsg

def solicitar_autorizacion(usuario, tipo_accion, modulo, id_registro):
    """
    Genera un código de autorización y lo envía al gerente por WhatsApp.
    """
    # Limpiar id_registro (si es 'N/A' o no numérico, poner None)
    try:
        id_registro = int(id_registro)
    except (ValueError, TypeError):
        id_registro = None

    # Expiración en 10 minutos
    expira = timezone.now() + timedelta(minutes=10)
    codigo = AutorizacionAccion.generar_codigo()
    
    # Guardar en BD
    autorizacion = AutorizacionAccion.objects.create(
        usuario_solicitante=usuario,
        codigo=codigo,
        tipo_accion=tipo_accion,
        modulo=modulo,
        id_registro=id_registro,
        fecha_expiracion=expira
    )
    
    # Obtener datos del gerente
    empresa = Empresa.objects.filter(activo=True).first()
    if not empresa or not empresa.celular_gerente:
        return False, "No se encontró el celular del gerente configurado."
    
    # Preparar mensaje
    mensaje = (
        f"⚠️ *SOLICITUD DE AUTORIZACIÓN*\n"
        f"━━━━━━━━━━━━━━━━━━━\n"
        f"👤 *Usuario:* {usuario.nombrecompleto}\n"
        f"⚡ *Acción:* {tipo_accion}\n"
        f"📁 *Módulo:* {modulo}\n"
        f"🆔 *ID Registro:* {id_registro}\n"
        f"━━━━━━━━━━━━━━━━━━━\n"
        f"🔑 *CÓDIGO:* `{codigo}`\n"
        f"━━━━━━━━━━━━━━━━━━━\n"
        f"⏰ Vence en 10 minutos."
    )
    
    # Enviar WhatsApp
    exito, msg = enviar_whatsapp_ultramsg(empresa.celular_gerente, mensaje)
    
    if exito:
        return True, "Código enviado al WhatsApp del gerente."
    else:
        return False, f"Error al enviar WhatsApp: {msg}"

def validar_codigo_autorizacion(usuario, codigo, tipo_accion, modulo, id_registro):
    """
    Valida si un código es correcto y vigente para una acción específica.
    """
    try:
        id_registro = int(id_registro)
    except (ValueError, TypeError):
        id_registro = None
        
    auth = AutorizacionAccion.objects.filter(
        codigo=codigo,
        tipo_accion=tipo_accion,
        modulo=modulo,
        id_registro=id_registro,
        usado=False
    ).first()
    
    if not auth:
        return False, "Código incorrecto o ya utilizado."
    
    if not auth.es_valido:
        return False, "El código ha expirado."
        
    # Marcar como usado
    auth.usado = True
    auth.save()
    
    return True, "Autorización concedida."
