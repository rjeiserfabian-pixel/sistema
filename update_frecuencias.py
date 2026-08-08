from software.models.CreditoModel import Credito
from software.models.CuotasVentaModel import CuotasVenta
from django.db import transaction

def update_frecuencias():
    creditos = Credito.objects.filter(frecuencia_pago='Personalizado')
    total = creditos.count()
    actualizados = {'Diario': 0, 'Semanal': 0, 'Quincenal': 0, 'Mensual': 0, 'Personalizado': 0}
    
    print(f"Buscando analizar {total} creditos...")
    
    with transaction.atomic():
        for credito in creditos:
            # Obtener cuotas ordenadas (excluyendo cuota_0 si la hubiera, aunque normálmente cuota_0 tiene monto_adelanto)
            # Generalmente la lógica se ve con las cuotas regulares (número > 0)
            cuotas = CuotasVenta.objects.filter(idcredito=credito, numero_cuota__gt=0).order_by('numero_cuota')
            
            if cuotas.count() >= 2:
                # Tomar las fechas de las dos primeras cuotas
                c1 = cuotas[0].fecha_vencimiento
                c2 = cuotas[1].fecha_vencimiento
                
                if c1 and c2:
                    diferencia = (c2 - c1).days
                    
                    if diferencia == 1:
                        nueva_frec = 'Diario'
                    elif diferencia == 7:
                        nueva_frec = 'Semanal'
                    elif diferencia in [14, 15, 16]:
                        nueva_frec = 'Quincenal'
                    elif diferencia >= 28 and diferencia <= 31:
                        nueva_frec = 'Mensual'
                    else:
                        nueva_frec = 'Personalizado'
                        
                    if nueva_frec != 'Personalizado':
                        credito.frecuencia_pago = nueva_frec
                        credito.save(update_fields=['frecuencia_pago'])
                        actualizados[nueva_frec] += 1
                    else:
                        actualizados['Personalizado'] += 1
            else:
                # Si solo tiene una cuota, es difícil inferir frecuencia, dejaremos Personalizado
                actualizados['Personalizado'] += 1
                
    print("\nResultados de actualizacion:")
    print(f"Diarios: {actualizados['Diario']}")
    print(f"Semanales: {actualizados['Semanal']}")
    print(f"Quincenales: {actualizados['Quincenal']}")
    print(f"Mensuales: {actualizados['Mensual']}")
    print(f"No cambiados (Personalizado): {actualizados['Personalizado']}")
    
update_frecuencias()
