from django.shortcuts import render, redirect
from django.http import HttpResponse
import os
from django.contrib import messages
from software.models.VentasModel import Ventas
from software.services.sunat_service import enviar_a_sunat

# Vista que lista todas las ventas (Boletas y Facturas) para su gestion con SUNAT
def lista_sunat(request):
    # Verificar sesión mínima
    if not request.session.get('idusuario'):
        return redirect('index')

    try:
        # Filtramos solo boletas y facturas
        # Por ahora obtenemos todas las ventas y mostramos las que tienen sunat_estado
        ventas = Ventas.objects.filter(estado=1).order_by('-idventa')[:1000] # Limitar a 1000 por ahora
        
        return render(request, 'software/sunat/lista.html', {
            'ventas': ventas,
            'titulo': 'Módulo SUNAT - Facturación Electrónica'
        })
    except Exception as e:
        import traceback
        print("ERROR EN MODULO SUNAT:")
        traceback.print_exc()
        messages.error(request, f"Error al cargar el módulo SUNAT: {str(e)}")
        # En vez de index, volver a cpanel o mostrar el error
        return render(request, 'errors/500_custom.html', {'error': str(e)}) if os.path.exists('templates/errors/500_custom.html') else HttpResponse(f"Error: {str(e)}")

# Endpoint para reenviar a SUNAT manualmente
def enviar_sunat_manual(request, idventa):
    try:
        exito, msg = enviar_a_sunat(idventa)
        if exito:
            messages.success(request, "Comprobante enviado a SUNAT correctamente.")
        else:
            messages.error(request, f"Ocurrió un error: {msg}")
    except Exception as e:
        messages.error(request, f"Excepción en el reenvío: {str(e)}")
        
    return redirect('lista_sunat')

# API interna para consultar tipo de cambio sin problemas de CORS en el frontend
from django.http import JsonResponse
import urllib.request
import json

def api_tipo_cambio(request):
    try:
        # Primer intento: API de SUNAT (apis.net.pe)
        url = 'https://api.apis.net.pe/v1/tipo-cambio-sunat'
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=5) as response:
            data = json.loads(response.read().decode('utf-8'))
            return JsonResponse(data)
    except Exception as e:
        # Segundo intento (Fallback): API global gratuita
        try:
            url_fallback = 'https://open.er-api.com/v6/latest/USD'
            req_fallback = urllib.request.Request(url_fallback, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req_fallback, timeout=5) as response:
                data = json.loads(response.read().decode('utf-8'))
                # Open.er-api solo da rate general, lo usamos para compra/venta en caso de emergencia
                rate = round(data['rates']['PEN'], 3)
                return JsonResponse({'compra': rate, 'venta': rate})
        except:
            return JsonResponse({'error': str(e)}, status=500)
