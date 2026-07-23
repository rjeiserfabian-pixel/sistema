from decimal import Decimal

from django.core.management.base import BaseCommand
from django.db import transaction

from software.models.CreditoModel import Credito
from software.models.RespuestoCompModel import RepuestoComp
from software.models.VehiculosModel import Vehiculo
from software.models.VentaDetalleModel import VentaDetalle
from software.models.VentasModel import Ventas


class Command(BaseCommand):
    help = "Audita ventas con detalles rotos, totales descuadrados o creditos con multiples vehiculos."

    def add_arguments(self, parser):
        parser.add_argument(
            "--idventa",
            type=int,
            help="Audita solo una venta especifica.",
        )
        parser.add_argument(
            "--fix",
            action="store_true",
            help="Anula con estado=0 los detalles activos que apuntan a vehiculos/repuestos inexistentes o sin producto.",
        )

    def handle(self, *args, **options):
        idventa = options.get("idventa")
        fix = options.get("fix")

        ventas = Ventas.objects.filter(estado=1).order_by("idventa")
        if idventa:
            ventas = ventas.filter(idventa=idventa)

        vehiculos_validos = set(
            Vehiculo.objects.filter(estado=1, idproducto__isnull=False)
            .values_list("id_vehiculo", flat=True)
        )
        repuestos_validos = set(
            RepuestoComp.objects.filter(estado=1, id_repuesto__isnull=False)
            .values_list("id_repuesto_comprado", flat=True)
        )
        ventas_credito = set(
            Credito.objects.filter(estado=1, idventa__isnull=False)
            .values_list("idventa_id", flat=True)
        )

        total_ventas = 0
        total_problemas = 0
        detalles_anulados = 0

        for venta in ventas:
            total_ventas += 1
            detalles = list(
                VentaDetalle.objects.filter(idventa=venta, estado=1).values(
                    "idventadetalle",
                    "tipo_item",
                    "id_vehiculo_id",
                    "id_repuesto_comprado_id",
                    "subtotal",
                )
            )

            invalidos = []
            vehiculos_activos_validos = []
            total_detalles = Decimal("0")
            total_detalles_validos = Decimal("0")

            for detalle in detalles:
                subtotal = detalle["subtotal"] or Decimal("0")
                total_detalles += subtotal
                tipo = detalle["tipo_item"]

                es_valido = True
                motivo = ""

                if tipo == "vehiculo":
                    id_vehiculo = detalle["id_vehiculo_id"]
                    if not id_vehiculo or id_vehiculo not in vehiculos_validos:
                        es_valido = False
                        motivo = f"vehiculo invalido id={id_vehiculo}"
                    else:
                        vehiculos_activos_validos.append(id_vehiculo)
                elif tipo == "repuesto":
                    id_repuesto = detalle["id_repuesto_comprado_id"]
                    if not id_repuesto or id_repuesto not in repuestos_validos:
                        es_valido = False
                        motivo = f"repuesto invalido id={id_repuesto}"
                else:
                    es_valido = False
                    motivo = f"tipo_item invalido={tipo}"

                if es_valido:
                    total_detalles_validos += subtotal
                else:
                    invalidos.append((detalle["idventadetalle"], motivo))

            problemas = []
            if invalidos:
                problemas.append(
                    "detalles_invalidos="
                    + ", ".join(f"{id_det} ({motivo})" for id_det, motivo in invalidos)
                )

            if total_detalles != venta.total_venta:
                problemas.append(
                    f"total_activos={total_detalles} total_venta={venta.total_venta}"
                )

            if total_detalles_validos != venta.total_venta:
                problemas.append(
                    f"total_validos={total_detalles_validos} total_venta={venta.total_venta}"
                )

            if venta.idventa in ventas_credito and len(set(vehiculos_activos_validos)) > 1:
                problemas.append(
                    "credito_con_multiples_vehiculos="
                    + ",".join(str(v) for v in sorted(set(vehiculos_activos_validos)))
                )

            if not problemas:
                continue

            total_problemas += 1
            self.stdout.write(
                self.style.WARNING(
                    f"Venta {venta.idventa} {venta.numero_comprobante}: "
                    + " | ".join(problemas)
                )
            )

            if fix and invalidos:
                ids_invalidos = [id_det for id_det, _ in invalidos]
                with transaction.atomic():
                    actualizados = VentaDetalle.objects.filter(
                        idventadetalle__in=ids_invalidos,
                        idventa=venta,
                        estado=1,
                    ).update(estado=0)
                detalles_anulados += actualizados
                self.stdout.write(
                    self.style.SUCCESS(
                        f"  Fix aplicado: {actualizados} detalle(s) invalidos anulados."
                    )
                )

        self.stdout.write(
            self.style.SUCCESS(
                f"Auditoria terminada. Ventas revisadas: {total_ventas}. "
                f"Ventas con problemas: {total_problemas}. "
                f"Detalles anulados: {detalles_anulados}."
            )
        )
