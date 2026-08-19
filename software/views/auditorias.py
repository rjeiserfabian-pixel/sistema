"""
Módulo de Auditorías - Vistas para todos los sub-módulos de auditoría.
Usa un Mixin base genérico que maneja paginación Server-Side de 10 en 10
para garantizar máximo rendimiento. Ningún endpoint trae más de 10 registros
a memoria por petición.
"""
import json
from django.shortcuts import render
from django.http import JsonResponse, HttpResponse
from django.db.models import Q
from django.views import View

from software.models.AuditoriaVentasModel import AuditoriaVentas
from software.models.AuditoriaComprasModel import AuditoriaCompras
from software.models.AuditoriaProductosModel import AuditoriaProductos
from software.models.AuditoriaCajasModel import AuditoriaCajas
from software.models.AuditoriaUsuariosModel import AuditoriaUsuarios
from software.models.AuditoriaCreditosModel import AuditoriaCreditos
from software.models.detalletipousuarioxmodulosModel import Detalletipousuarioxmodulos

PAGE_SIZE = 10  # Paginación estricta de 10 en 10


# ---------------------------------------------------------------------------
# Mixin Base - Server-Side DataTables con paginación de 10 en 10
# ---------------------------------------------------------------------------

class BaseAuditoriaDatatableView(View):
    """
    Clase base genérica para todas las vistas AJAX de Auditoría.
    Las subclases solo deben definir:
        - model: el modelo de auditoría
        - search_fields: lista de campos para buscar
        - serialize_row(instance): método para serializar cada fila
    """
    model = None
    search_fields = []
    queryset = None

    def _get_base_queryset(self):
        if self.queryset is not None:
            qs = self.queryset
        else:
            qs = self.model.objects.all()
            
        # Evitar crash de psycopg2/Django por JSONFields omitiendo su carga
        # ya que no se muestran en las tablas
        json_fields = ['datos_anteriores', 'datos_nuevos']
        existing_fields = [f.name for f in self.model._meta.get_fields()]
        fields_to_defer = [f for f in json_fields if f in existing_fields]
        if fields_to_defer:
            qs = qs.defer(*fields_to_defer)
            
        return qs

    def get(self, request, *args, **kwargs):
        # Parámetros estándar de DataTables server-side
        draw = int(request.GET.get('draw', 1))
        start = int(request.GET.get('start', 0))
        # Forzar siempre PAGE_SIZE sin importar lo que pida el cliente
        length = PAGE_SIZE
        search_value = request.GET.get('search[value]', '').strip()
        fecha_inicio = request.GET.get('fecha_inicio', '').strip()
        fecha_fin = request.GET.get('fecha_fin', '').strip()
        usuario_filter = request.GET.get('usuario', '').strip()

        qs = self._get_base_queryset()

        # Búsqueda global por texto
        if search_value and self.search_fields:
            q_filter = Q()
            for field in self.search_fields:
                q_filter |= Q(**{f'{field}__icontains': search_value})
            qs = qs.filter(q_filter)

        # Filtro por rango de fechas (campo genérico fecha_auditoria o fecha)
        fecha_field = self._get_fecha_field()
        if fecha_inicio:
            qs = qs.filter(**{f'{fecha_field}__date__gte': fecha_inicio})
        if fecha_fin:
            qs = qs.filter(**{f'{fecha_field}__date__lte': fecha_fin})

        # Filtro por usuario (nombrecompleto)
        if usuario_filter:
            qs = qs.filter(
                Q(idusuario__nombrecompleto__icontains=usuario_filter)
            )

        records_total = self._get_base_queryset().count()
        records_filtered = qs.count()

        # Aplicar paginación estricta de 10 en 10
        qs = self.apply_select_related(qs)
        page_qs = qs[start:start + length]

        data = [self.serialize_row(row) for row in page_qs]

        return JsonResponse({
            'draw': draw,
            'recordsTotal': records_total,
            'recordsFiltered': records_filtered,
            'data': data,
        })

    def _get_fecha_field(self):
        """Retorna el nombre del campo de fecha del modelo."""
        if hasattr(self.model, 'fecha_auditoria'):
            return 'fecha_auditoria'
        return 'fecha'

    def apply_select_related(self, qs):
        """Subclases pueden sobreescribir para agregar select_related."""
        return qs.select_related('idusuario')

    def serialize_row(self, instance):
        raise NotImplementedError("Las subclases deben implementar serialize_row()")


def _format_fecha(dt):
    return dt.strftime('%d/%m/%Y %I:%M %p') if dt else '-'


def _format_usuario(instance):
    try:
        u = instance.idusuario
        return u.nombrecompleto or '-'
    except Exception:
        return '-'


# ---------------------------------------------------------------------------
# Vistas de Renderizado de Páginas
# ---------------------------------------------------------------------------

def _check_session(request):
    return request.session.get('idtipousuario')


def auditorias_ventas(request):
    id2 = _check_session(request)
    if not id2:
        return HttpResponse("<h1>No tiene acceso</h1>")
    permisos = Detalletipousuarioxmodulos.objects.filter(idtipousuario=id2)
    return render(request, 'auditorias/ventas.html', {'permisos': permisos})


def auditorias_compras(request):
    id2 = _check_session(request)
    if not id2:
        return HttpResponse("<h1>No tiene acceso</h1>")
    permisos = Detalletipousuarioxmodulos.objects.filter(idtipousuario=id2)
    return render(request, 'auditorias/compras.html', {'permisos': permisos})


def auditorias_productos(request):
    id2 = _check_session(request)
    if not id2:
        return HttpResponse("<h1>No tiene acceso</h1>")
    permisos = Detalletipousuarioxmodulos.objects.filter(idtipousuario=id2)
    return render(request, 'auditorias/productos.html', {'permisos': permisos})


def auditorias_cajas(request):
    id2 = _check_session(request)
    if not id2:
        return HttpResponse("<h1>No tiene acceso</h1>")
    permisos = Detalletipousuarioxmodulos.objects.filter(idtipousuario=id2)
    return render(request, 'auditorias/cajas.html', {'permisos': permisos})


def auditorias_usuarios(request):
    id2 = _check_session(request)
    if not id2:
        return HttpResponse("<h1>No tiene acceso</h1>")
    permisos = Detalletipousuarioxmodulos.objects.filter(idtipousuario=id2)
    return render(request, 'auditorias/usuarios.html', {'permisos': permisos})


def auditorias_creditos(request):
    id2 = _check_session(request)
    if not id2:
        return HttpResponse("<h1>No tiene acceso</h1>")
    permisos = Detalletipousuarioxmodulos.objects.filter(idtipousuario=id2)
    return render(request, 'auditorias/creditos.html', {'permisos': permisos})


# ---------------------------------------------------------------------------
# Vistas AJAX - Server-Side DataTables (una por sub-módulo)
# ---------------------------------------------------------------------------

class AuditoriaVentasJsonView(BaseAuditoriaDatatableView):
    model = AuditoriaVentas
    search_fields = ['accion', 'motivo', 'idusuario__nombrecompleto']

    def serialize_row(self, instance):
        return {
            'id': instance.idauditoria_venta,
            'idventa': instance.idventa,
            'accion': instance.accion or '-',
            'motivo': instance.motivo or '-',
            'usuario': _format_usuario(instance),
            'fecha': _format_fecha(instance.fecha_auditoria),
        }


class AuditoriaComprasJsonView(BaseAuditoriaDatatableView):
    model = AuditoriaCompras
    search_fields = ['accion', 'motivo', 'idusuario__nombrecompleto']

    def _get_fecha_field(self):
        return 'fecha'

    def serialize_row(self, instance):
        return {
            'id': instance.idauditoria,
            'idcompra': instance.idcompra,
            'accion': instance.accion or '-',
            'motivo': instance.motivo or '-',
            'usuario': _format_usuario(instance),
            'fecha': _format_fecha(instance.fecha),
        }

    def apply_select_related(self, qs):
        return qs.select_related('idusuario')


class AuditoriaProductosJsonView(BaseAuditoriaDatatableView):
    model = AuditoriaProductos
    search_fields = ['accion', 'motivo', 'idusuario__nombrecompleto', 'idproducto__nomproducto']

    def apply_select_related(self, qs):
        return qs.select_related('idusuario', 'idproducto')

    def serialize_row(self, instance):
        try:
            prod_nombre = instance.idproducto.nomproducto
        except Exception:
            prod_nombre = f'#{instance.idproducto_id}'
        return {
            'id': instance.idauditoria_producto,
            'producto': prod_nombre,
            'accion': instance.accion or '-',
            'motivo': instance.motivo or '-',
            'usuario': _format_usuario(instance),
            'fecha': _format_fecha(instance.fecha_auditoria),
        }


class AuditoriaCajasJsonView(BaseAuditoriaDatatableView):
    model = AuditoriaCajas
    search_fields = ['accion', 'motivo', 'detalles', 'idusuario__nombrecompleto']

    def apply_select_related(self, qs):
        return qs.select_related('idusuario', 'id_caja')

    def serialize_row(self, instance):
        try:
            caja_nombre = instance.id_caja.nombre_caja if instance.id_caja else '-'
        except Exception:
            caja_nombre = '-'
        return {
            'id': instance.idauditoria_caja,
            'caja': caja_nombre,
            'accion': instance.accion or '-',
            'motivo': instance.motivo or '-',
            'detalles': instance.detalles or '-',
            'usuario': _format_usuario(instance),
            'fecha': _format_fecha(instance.fecha_auditoria),
        }


class AuditoriaUsuariosJsonView(BaseAuditoriaDatatableView):
    model = AuditoriaUsuarios
    search_fields = ['accion', 'motivo', 'detalles', 'usuario_afectado__nombrecompleto']

    def apply_select_related(self, qs):
        return qs.select_related('usuario_afectado', 'usuario_responsable')

    def _get_fecha_field(self):
        return 'fecha_auditoria'

    def serialize_row(self, instance):
        try:
            ua = instance.usuario_afectado
            afectado_str = ua.nombrecompleto or '-'
        except Exception:
            afectado_str = '-'
        try:
            ur = instance.usuario_responsable
            responsable_str = ur.nombrecompleto if ur else 'Sistema'
        except Exception:
            responsable_str = '-'
        return {
            'id': instance.idauditoria_usuario,
            'usuario_afectado': afectado_str,
            'usuario_responsable': responsable_str,
            'accion': instance.accion or '-',
            'motivo': instance.motivo or '-',
            'ip': instance.ip_address or '-',
            'fecha': _format_fecha(instance.fecha_auditoria),
        }

    def get(self, request, *args, **kwargs):
        # Sobreescribir para usar usuario_afectado en vez de idusuario para filtro por usuario
        draw = int(request.GET.get('draw', 1))
        start = int(request.GET.get('start', 0))
        length = PAGE_SIZE
        search_value = request.GET.get('search[value]', '').strip()
        fecha_inicio = request.GET.get('fecha_inicio', '').strip()
        fecha_fin = request.GET.get('fecha_fin', '').strip()
        usuario_filter = request.GET.get('usuario', '').strip()

        qs = self._get_base_queryset()

        if search_value:
            qs = qs.filter(
                Q(accion__icontains=search_value) |
                Q(motivo__icontains=search_value) |
                Q(detalles__icontains=search_value) |
                Q(usuario_afectado__nombrecompleto__icontains=search_value)
            )

        if fecha_inicio:
            qs = qs.filter(fecha_auditoria__date__gte=fecha_inicio)
        if fecha_fin:
            qs = qs.filter(fecha_auditoria__date__lte=fecha_fin)
        if usuario_filter:
            qs = qs.filter(
                Q(usuario_afectado__nombrecompleto__icontains=usuario_filter)
            )

        records_total = self._get_base_queryset().count()
        records_filtered = qs.count()
        page_qs = self.apply_select_related(qs)[start:start + length]
        data = [self.serialize_row(row) for row in page_qs]

        return JsonResponse({
            'draw': draw,
            'recordsTotal': records_total,
            'recordsFiltered': records_filtered,
            'data': data,
        })


class AuditoriaCreditosJsonView(BaseAuditoriaDatatableView):
    model = AuditoriaCreditos
    search_fields = ['accion', 'motivo', 'detalles', 'idusuario__nombrecompleto']

    def serialize_row(self, instance):
        return {
            'id': instance.idauditoria_credito,
            'idcredito': instance.idcredito,
            'accion': instance.accion or '-',
            'motivo': instance.motivo or '-',
            'detalles': instance.detalles or '-',
            'usuario': _format_usuario(instance),
            'fecha': _format_fecha(instance.fecha_auditoria),
        }
