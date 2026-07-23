from collections import defaultdict
from django.shortcuts import render, redirect
from django.http import HttpResponse
from software.models.detalletipousuarioxmodulosModel import Detalletipousuarioxmodulos
from software.models.ModulosModel import Modulos
from software.models.TipousuarioModel import Tipousuario

def permisos(request):
    id2 = request.session.get('idtipousuario')
    if id2:
        # Obtener permisos del usuario
        permisos = Detalletipousuarioxmodulos.objects.filter(
            idtipousuario=id2
        ).select_related('idmodulo', 'idmodulo__idmodulo_padre')
        
        # Organizar módulos en estructura jerárquica
        modulos_organizados = {}
        
        for permiso in permisos:
            modulo = permiso.idmodulo
            
            # Si el módulo tiene padre
            if modulo.idmodulo_padre:
                padre = modulo.idmodulo_padre
                padre_nombre = padre.nombremodulo
                
                # Crear entrada del padre si no existe
                if padre_nombre not in modulos_organizados:
                    modulos_organizados[padre_nombre] = {
                        'padre': padre,
                        'hijos': []
                    }
                # Agregar el hijo
                modulos_organizados[padre_nombre]['hijos'].append(modulo)
            else:
                # Es módulo padre o independiente
                if modulo.nombremodulo not in modulos_organizados:
                    modulos_organizados[modulo.nombremodulo] = {
                        'padre': modulo,
                        'hijos': []
                    }
        
        # Ordenar hijos por orden
        for nombre, grupo in modulos_organizados.items():
            grupo['hijos'].sort(key=lambda x: x.orden if x.orden is not None else 0)
            
        # Ordenar el diccionario principal por el orden del padre
        modulos_organizados = dict(sorted(
            modulos_organizados.items(),
            key=lambda item: item[1]['padre'].orden if item[1]['padre'].orden is not None else 0
        ))
        
        # Datos para gestión de permisos
        permisos2 = Detalletipousuarioxmodulos.objects.filter(idtipousuario__estado=1)
        modulos = Modulos.objects.filter(estado=1)
        tipoUsuarios = Tipousuario.objects.filter(estado=1)
        
        permisos_por_tipo_usuario = defaultdict(list)
        for permiso in permisos2:
            permisos_por_tipo_usuario[permiso.idtipousuario.nombretipousuario].append(permiso)
        
        # Organizar TODOS los módulos activos en estructura jerárquica para el modal
        todos_modulos_organizados = {}
        modulos_con_padre = modulos.select_related('idmodulo_padre')
        
        for modulo in modulos_con_padre:
            if modulo.idmodulo_padre:
                padre = modulo.idmodulo_padre
                key = padre.idmodulo
                if key not in todos_modulos_organizados:
                    todos_modulos_organizados[key] = {
                        'padre': padre,
                        'hijos': []
                    }
                todos_modulos_organizados[key]['hijos'].append(modulo)
            else:
                # Módulo sin padre (es raíz)
                key = modulo.idmodulo
                if key not in todos_modulos_organizados:
                    todos_modulos_organizados[key] = {
                        'padre': modulo,
                        'hijos': []
                    }
        
        # Ordenar por orden del padre
        todos_modulos_organizados = dict(sorted(
            todos_modulos_organizados.items(),
            key=lambda item: item[1]['padre'].orden if item[1]['padre'].orden is not None else 0
        ))
        # Ordenar hijos
        for key, grupo in todos_modulos_organizados.items():
            grupo['hijos'].sort(key=lambda x: x.orden if x.orden is not None else 0)
            
        data = {
            'permisos_por_tipo_usuario': permisos_por_tipo_usuario.items(),
            'permisos': permisos,
            'modulos_organizados': modulos_organizados,
            'modulos': modulos,
            'tipoUsuarios': tipoUsuarios,
            'todos_modulos_organizados': todos_modulos_organizados.values(),
        }
        
        return render(request, 'permisos/permisos.html', data)
    else:
        return HttpResponse("<h1>No tiene acceso señor</h1>")

def agregaPermiso(request):
    idTipoUsuario2 = request.POST.get('tipoUsuario')
    permisos = request.POST.getlist("permisosTu[idmodulo][]")
    
    getTipoUsuarios = Tipousuario.objects.get(idtipousuario=idTipoUsuario2)
    
    for idPErmiso in permisos:
        
        modulo = Modulos.objects.get(idmodulo=idPErmiso)
        
        newPermiso = Detalletipousuarioxmodulos()
        newPermiso.idtipousuario = getTipoUsuarios
        newPermiso.idmodulo=modulo
        newPermiso.save()
    
    return redirect('permisos')


def editarPermiso(request):
    """
    Edita los permisos de un tipo de usuario específico
    Elimina los permisos existentes y crea los nuevos seleccionados
    """
    if request.method == 'POST':
        idTipoUsuario = request.POST.get('idTipoUsuario')
        permisos = request.POST.getlist("permisosEdit[idmodulo][]")
        
        try:
            # Obtener el tipo de usuario
            getTipoUsuarios = Tipousuario.objects.get(idtipousuario=idTipoUsuario)
            
            # Eliminar los permisos existentes de este tipo de usuario
            Detalletipousuarioxmodulos.objects.filter(idtipousuario=idTipoUsuario).delete()
            
            # Crear los nuevos permisos seleccionados
            for idPermiso in permisos:
                modulo = Modulos.objects.get(idmodulo=idPermiso)
                
                newPermiso = Detalletipousuarioxmodulos()
                newPermiso.idtipousuario = getTipoUsuarios
                newPermiso.idmodulo = modulo
                newPermiso.save()
            
            return redirect('permisos')
            
        except Exception as e:
            return HttpResponse(f"<h1>Error al editar permisos: {str(e)}</h1>")
    
    return redirect('permisos')


def eliminarPermiso(request,id):
    Detalletipousuarioxmodulos.objects.filter(idtipousuario=id).delete()
    return redirect('permisos')