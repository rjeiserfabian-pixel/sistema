import os, django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'raiz.settings')
django.setup()

from software.models.VehiculosModel import Vehiculo
from software.models.VentaDetalleModel import VentaDetalle
from software.models.CreditoModel import Credito
from django.db.models import Sum, Count
from django.db.models.functions import Coalesce

# Find a vehicle that was re-sold (i.e. has multiple ventadetalle records)
v = Vehiculo.objects.annotate(c=Count('ventadetalle')).filter(c__gt=1).first()
if not v:
    v = Vehiculo.objects.filter(ventadetalle__isnull=False).first()

if v:
    print('Vehiculo:', v.id_vehiculo, getattr(v.idproducto, 'nomproducto', ''), v.serie_chasis)
    detalles = VentaDetalle.objects.filter(id_vehiculo=v).order_by('idventa__fecha_venta')
    
    total_recaudado = 0
    for d in detalles:
        if not d.idventa:
            continue
            
        print(f'  Venta {d.idventa.idventa} - Comprobante: {d.idventa.numero_comprobante} - Fecha: {d.idventa.fecha_venta} - Estado: {d.estado}')
        
        credito = Credito.objects.filter(idventa=d.idventa).first()
        if credito:
            print(f'    Credito {credito.idcredito} - Estado: {credito.estado_credito} - Adelanto: {credito.monto_adelanto}')
            
            from software.models.PagoCuotaModel import PagoCuota
            pagos = PagoCuota.objects.filter(idcuotaventa__idcredito=credito, estado=1).aggregate(t=Coalesce(Sum('monto_pago'), 0.0))['t']
            print(f'    Pagos de cuotas: {pagos}')
            
            total_recaudado += float(credito.monto_adelanto or 0) + float(pagos)
        else:
            print(f'    Venta al contado. Subtotal vehiculo: {d.subtotal}')
            total_recaudado += float(d.subtotal)
            
    print(f'TOTAL RECAUDADO POR ESTE VEHICULO: {total_recaudado}')
