"""
software/utils/credito_cuotas.py
─────────────────────────────────
Helper centralizado para la validación de pago secuencial de cuotas.

Regla de negocio:
  - La cuota inicial (numero_cuota = 0) siempre puede pagarse libremente.
  - Desde numero_cuota >= 1, cada cuota solo puede pagarse si TODAS las
    cuotas con numero_cuota menor (>= 1) están en estado 'Pagado'.
  - Los estados 'Pendiente' y 'Parcial' bloquean el avance.
  - Esta lógica aplica SOLO en el módulo de Créditos.

Diseño para escalabilidad:
  - Una sola query por crédito usando .values() (datos planos, sin ORM pesado).
  - Recorrido lineal O(n) para calcular bloqueos.
  - Punto único de cambio: si la regla evoluciona, solo se edita este archivo.
"""

from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from software.models.CreditoModel import Credito
    from software.models.CuotasVentaModel import CuotasVenta


# ─────────────────────────────────────────────────────────────────────────────
# Función principal — Una sola query para todos los estados de bloqueo
# ─────────────────────────────────────────────────────────────────────────────

def obtener_estados_bloqueo(credito: "Credito") -> dict:
    """
    Calcula en UNA sola query qué cuotas pueden pagarse según el orden
    secuencial. La cuota inicial (numero_cuota=0) siempre puede pagarse.
    La validación aplica desde numero_cuota >= 1.

    Args:
        credito: Instancia del modelo Credito.

    Returns:
        dict { idcuotaventa (int): {
                   'puede_pagar':       bool,
                   'bloqueante_numero': int | None,
               } }
    """
    from software.models.CuotasVentaModel import CuotasVenta

    # Filtro base según tipo de crédito (por venta o directo)
    if credito.idventa_id:
        qs = CuotasVenta.objects.filter(
            idventa_id=credito.idventa_id,
            estado=1,
        )
    else:
        qs = CuotasVenta.objects.filter(
            idcredito_id=credito.idcredito,
            estado=1,
        )

    # Una sola query — solo los campos necesarios, sin objetos ORM completos
    filas = list(
        qs.order_by('numero_cuota')
          .values('idcuotaventa', 'numero_cuota', 'estado_pago')
    )

    # Recorrido lineal para detectar el primer bloqueante (>= 1, no 'Pagado')
    primer_bloqueante_numero: int | None = None
    resultado: dict = {}

    for fila in filas:
        num    = fila['numero_cuota']
        id_c   = fila['idcuotaventa']
        estado = fila['estado_pago']

        # La cuota inicial siempre está libre — no actúa como bloqueante
        if num == 0:
            resultado[id_c] = {'puede_pagar': True, 'bloqueante_numero': None}
            continue

        # Registrar el primer bloqueante si aún no lo teníamos
        if primer_bloqueante_numero is None and estado != 'Pagado':
            primer_bloqueante_numero = num

        # Esta cuota puede pagarse solo si no hay ningún bloqueante ANTES de ella
        puede = (
            primer_bloqueante_numero is None
            or primer_bloqueante_numero >= num
        )
        resultado[id_c] = {
            'puede_pagar': puede,
            'bloqueante_numero': None if puede else primer_bloqueante_numero,
        }

    return resultado


# ─────────────────────────────────────────────────────────────────────────────
# Validación para pago individual
# ─────────────────────────────────────────────────────────────────────────────

def validar_pago_secuencial(cuota: "CuotasVenta", credito: "Credito") -> str | None:
    """
    Valida si una cuota individual puede pagarse según el orden secuencial.

    Args:
        cuota:   Instancia de CuotasVenta que se quiere pagar.
        credito: Instancia de Credito al que pertenece la cuota.

    Returns:
        str  con el mensaje de error si el pago NO está permitido.
        None si el pago sí está permitido.

    Uso en vistas:
        error = validar_pago_secuencial(cuota, credito)
        if error:
            return JsonResponse({'ok': False, 'error': error}, status=400)
    """
    # La cuota inicial nunca se valida — siempre libre
    if cuota.numero_cuota == 0:
        return None

    estados = obtener_estados_bloqueo(credito)
    info = estados.get(cuota.idcuotaventa)

    if info and not info['puede_pagar']:
        num = info['bloqueante_numero']
        num_display = 'Inicial' if num == 0 else f'#{num}'
        return (
            f"No puedes pagar la cuota #{cuota.numero_cuota} porque la cuota "
            f"{num_display} aún no ha sido completamente pagada. "
            f"Las cuotas deben pagarse en orden."
        )

    return None


# ─────────────────────────────────────────────────────────────────────────────
# Validación para pago múltiple
# ─────────────────────────────────────────────────────────────────────────────

def validar_seleccion_multiple(cuotas, credito: "Credito") -> str | None:
    """
    Valida que el conjunto de cuotas seleccionadas para pago múltiple sea
    válido: sin cuotas anteriores bloqueantes y estrictamente consecutivas.

    Args:
        cuotas:  Queryset o lista de instancias CuotasVenta seleccionadas.
        credito: Instancia de Credito al que pertenecen.

    Returns:
        str  con el mensaje de error si la selección NO es válida.
        None si la selección es válida.
    """
    # Números de cuotas regulares (>= 1) ordenados
    numeros = sorted(
        c.numero_cuota for c in cuotas if c.numero_cuota >= 1
    )

    # Si solo se seleccionó la cuota inicial o ninguna regular, está bien
    if not numeros:
        return None

    # 1. Verificar que no hay bloqueantes ANTES del mínimo seleccionado
    estados = obtener_estados_bloqueo(credito)
    id_primera = next(
        (c.idcuotaventa for c in cuotas if c.numero_cuota == numeros[0]),
        None,
    )
    if id_primera is not None:
        info = estados.get(id_primera)
        if info and not info['puede_pagar']:
            num = info['bloqueante_numero']
            num_display = 'Inicial' if num == 0 else f'#{num}'
            return (
                f"No puedes pagar las cuotas seleccionadas porque la cuota "
                f"{num_display} aún no ha sido completamente pagada."
            )

    # 2. Verificar que las cuotas seleccionadas son estrictamente consecutivas
    for i in range(len(numeros) - 1):
        if numeros[i + 1] - numeros[i] > 1:
            return (
                f"Las cuotas seleccionadas no son consecutivas. "
                f"Debes pagar la cuota #{numeros[i] + 1} antes de la "
                f"#{numeros[i + 1]}."
            )

    return None
