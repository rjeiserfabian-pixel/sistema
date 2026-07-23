"""
Módulo de compatibilidad para consultas de DNI y RUC.

Mantiene la interfaz pública original (consultar_dni, consultar_ruc,
consultar_documento) para no modificar las vistas que ya lo consumen
(clientes.py, garantes.py, proveedores.py).

Internamente delega toda la lógica al ConsultaOrchestrator, que implementa
el failover automático entre DeColecta (principal) y APIsPERU (respaldo).
"""

import logging
from typing import Dict, Optional

logger = logging.getLogger(__name__)

# ── Importación lazy del orquestador para evitar problemas de startup ─────────
_orchestrator = None

def _get_orchestrator():
    """
    Devuelve la instancia global del orquestador, creándola en el primer uso.
    Usar lazy initialization evita errores de importación durante el arranque
    de Django (antes de que settings esté completamente cargado).
    """
    global _orchestrator
    if _orchestrator is None:
        from software.services.dni_ruc_service import ConsultaOrchestrator
        _orchestrator = ConsultaOrchestrator()
    return _orchestrator


# ==============================================================================
# API PÚBLICA — Mismas firmas que antes, ahora con failover automático
# ==============================================================================

def consultar_dni(dni: str, token: Optional[str] = None) -> Dict:
    """
    Consulta información de una persona por DNI usando RENIEC.

    Utiliza failover automático:
      1. Intenta con DeColecta (principal)
      2. Si falla, usa APIsPERU (respaldo)

    Args:
        dni: Número de DNI (8 dígitos numéricos)
        token: Ignorado — las credenciales se leen desde settings.py

    Returns:
        Dict con claves estándar:
            dni, nombres, apellido_paterno, apellido_materno,
            nombre_completo, codigo_verificacion, fecha_nacimiento,
            sexo, ubigeo, direccion

    Raises:
        ValueError: Si el DNI es inválido o todos los proveedores fallan
    """
    if not dni or len(str(dni)) not in (7, 8) or not str(dni).isdigit():
        raise ValueError("El DNI debe tener 7 u 8 dígitos numéricos")
    
    dni_str = str(dni).zfill(8)
    return _get_orchestrator().consultar_dni(dni_str)


def consultar_ruc(ruc: str, token: Optional[str] = None) -> Dict:
    """
    Consulta información de una empresa por RUC usando SUNAT.

    Utiliza failover automático:
      1. Intenta con DeColecta (principal)
      2. Si falla, usa APIsPERU (respaldo)

    Args:
        ruc: Número de RUC (11 dígitos numéricos)
        token: Ignorado — las credenciales se leen desde settings.py

    Returns:
        Dict con claves estándar:
            ruc, razon_social, nombre_comercial, tipo_contribuyente,
            estado, condicion, direccion, departamento, provincia,
            distrito, ubigeo, fecha_inscripcion, actividad_economica,
            via_tipo, via_nombre, numero, interior, lote,
            departamento_dir, manzana, kilometro,
            es_agente_retencion, es_buen_contribuyente

    Raises:
        ValueError: Si el RUC es inválido o todos los proveedores fallan
    """
    if not ruc or len(str(ruc)) != 11 or not str(ruc).isdigit():
        raise ValueError("El RUC debe tener 11 dígitos numéricos")
    return _get_orchestrator().consultar_ruc(str(ruc))


def consultar_documento(numero: str, token: Optional[str] = None) -> Dict:
    """
    Función inteligente que detecta si el número es DNI (8 dígitos) o
    RUC (11 dígitos) y realiza la consulta correspondiente con failover
    automático entre proveedores.

    Args:
        numero: Número de documento (8 dígitos = DNI, 11 dígitos = RUC)
        token: Ignorado — las credenciales se leen desde settings.py

    Returns:
        Dict con los datos del documento más las claves adicionales:
            tipo_documento: 'DNI' o 'RUC'
            id_tipo_entidad: 1 (DNI) o 6 (RUC) según la tabla tipo_entidad

    Raises:
        ValueError: Si el documento es inválido o todos los proveedores fallan
    """
    if not numero or not str(numero).isdigit():
        raise ValueError("El número de documento debe contener solo dígitos")

    numero = str(numero).strip()

    if len(numero) in (7, 8):
        resultado = consultar_dni(numero)
        resultado['tipo_documento'] = 'DNI'
        resultado['id_tipo_entidad'] = 1   # DNI según tabla tipo_entidad del proyecto
        return resultado

    elif len(numero) == 11:
        resultado = consultar_ruc(numero)
        resultado['tipo_documento'] = 'RUC'
        resultado['id_tipo_entidad'] = 6   # RUC según tabla tipo_entidad del proyecto
        return resultado

    else:
        raise ValueError(
            f"Longitud de documento inválida ({len(numero)} dígitos). "
            "Se esperan 7 u 8 dígitos para DNI o 11 dígitos para RUC."
        )


# ==============================================================================
# CLASE LEGACY — Mantenida por compatibilidad con código antiguo si existiera
# ==============================================================================

class TokenPeruAPI:
    """
    Clase de compatibilidad. Internamente usa el ConsultaOrchestrator.
    Mantenida para evitar romper importaciones de código externo si las hubiera.
    """

    def __init__(self, token: Optional[str] = None):
        # El token se ignora; las credenciales vienen de settings.py
        logger.debug(
            "TokenPeruAPI instanciado. "
            "Las credenciales se leen desde settings.TOKENPERU_TOKEN y "
            "settings.APISPERU_TOKEN."
        )

    def consultar_dni(self, dni: str) -> Dict:
        return consultar_dni(dni)

    def consultar_ruc(self, ruc: str) -> Dict:
        return consultar_ruc(ruc)

    def consultar_ruc_completo(self, ruc: str) -> Dict:
        """Alias de consultar_ruc para compatibilidad con código previo."""
        return consultar_ruc(ruc)