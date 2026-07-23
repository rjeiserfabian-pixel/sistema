import requests
from software.models.empresaModel import Empresa

def enviar_whatsapp_ultramsg(numero, mensaje):
    """
    Envía un mensaje de WhatsApp usando la API de UltraMsg.
    """
    try:
        empresa = Empresa.objects.filter(activo=True).first()
        if not empresa or not empresa.ultramsg_instance or not empresa.ultramsg_token:
            print("❌ UltraMsg: Configuración incompleta en la empresa.")
            return False, "Configuración incompleta"

        instance_id = empresa.ultramsg_instance
        token = empresa.ultramsg_token
        
        # Limpiar número (quitar espacios, +, etc)
        numero_limpio = "".join(filter(str.isdigit, str(numero)))
        # Asegurar prefijo de país (Perú +51 por defecto si tiene 9 dígitos)
        if len(numero_limpio) == 9:
            numero_limpio = "51" + numero_limpio

        url = f"https://api.ultramsg.com/{instance_id}/messages/chat"
        
        payload = {
            "token": token,
            "to": numero_limpio,
            "body": mensaje,
            "priority": 10
        }
        
        headers = {'content-type': 'application/x-www-form-urlencoded'}
        
        response = requests.post(url, data=payload, headers=headers, timeout=10)
        res_json = response.json()
        
        if response.status_code == 200 and res_json.get('sent') == 'true':
            print(f"✅ WhatsApp enviado a {numero_limpio}")
            return True, "Enviado"
        else:
            print(f"❌ Error UltraMsg: {res_json}")
            return False, res_json.get('error', 'Error desconocido')
            
    except Exception as e:
        print(f"❌ Exception UltraMsg: {str(e)}")
        return False, str(e)
