from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from django.contrib import messages
from software.models.transporteVehiculoModel import TransporteVehiculo
from software.models.transporteConductorModel import TransporteConductor

# --- CRUD VEHÍCULOS ---

def lista_vehiculos_transporte(request):
    vehiculos = TransporteVehiculo.objects.all().order_by('placa')
    return render(request, 'transporte/vehiculos.html', {'vehiculos': vehiculos})

def agregar_vehiculo_transporte(request):
    if request.method == 'POST':
        try:
            TransporteVehiculo.objects.create(
                placa=request.POST.get('placa').upper(),
                marca=request.POST.get('marca'),
                modelo=request.POST.get('modelo'),
                tipo=request.POST.get('tipo'),
                capacidad=request.POST.get('capacidad'),
                estado='disponible'
            )
            messages.success(request, 'Vehículo registrado exitosamente')
        except Exception as e:
            messages.error(request, f'Error al registrar: {str(e)}')
    return redirect('lista_vehiculos_transporte')

def editar_vehiculo_transporte(request):
    if request.method == 'POST':
        id_v = request.POST.get('id_transporte_vehiculo')
        vehiculo = get_object_or_404(TransporteVehiculo, id_transporte_vehiculo=id_v)
        try:
            vehiculo.placa = request.POST.get('placa').upper()
            vehiculo.marca = request.POST.get('marca')
            vehiculo.modelo = request.POST.get('modelo')
            vehiculo.tipo = request.POST.get('tipo')
            vehiculo.capacidad = request.POST.get('capacidad')
            vehiculo.estado = request.POST.get('estado')
            vehiculo.save()
            messages.success(request, 'Vehículo actualizado')
        except Exception as e:
            messages.error(request, f'Error al actualizar: {str(e)}')
    return redirect('lista_vehiculos_transporte')

def eliminar_vehiculo_transporte(request, id):
    vehiculo = get_object_or_404(TransporteVehiculo, id_transporte_vehiculo=id)
    try:
        vehiculo.delete()
        messages.success(request, 'Vehículo eliminado')
    except Exception:
        messages.error(request, 'No se puede eliminar el vehículo porque tiene traslados asociados')
    return redirect('lista_vehiculos_transporte')


# --- CRUD CONDUCTORES ---

def lista_conductores(request):
    conductores = TransporteConductor.objects.all().order_by('nombre_completo')
    return render(request, 'transporte/conductores.html', {'conductores': conductores})

def agregar_conductor(request):
    if request.method == 'POST':
        try:
            TransporteConductor.objects.create(
                nombre_completo=request.POST.get('nombre_completo'),
                dni=request.POST.get('dni'),
                licencia_conducir=request.POST.get('licencia_conducir').upper(),
                tipo_licencia=request.POST.get('tipo_licencia').upper(),
                telefono=request.POST.get('telefono'),
                estado='disponible'
            )
            messages.success(request, 'Conductor registrado exitosamente')
        except Exception as e:
            messages.error(request, f'Error al registrar: {str(e)}')
    return redirect('lista_conductores')

def editar_conductor(request):
    if request.method == 'POST':
        id_c = request.POST.get('id_transporte_conductor')
        conductor = get_object_or_404(TransporteConductor, id_transporte_conductor=id_c)
        try:
            conductor.nombre_completo = request.POST.get('nombre_completo')
            conductor.dni = request.POST.get('dni')
            conductor.licencia_conducir = request.POST.get('licencia_conducir').upper()
            conductor.tipo_licencia = request.POST.get('tipo_licencia').upper()
            conductor.telefono = request.POST.get('telefono')
            conductor.estado = request.POST.get('estado')
            conductor.save()
            messages.success(request, 'Conductor actualizado')
        except Exception as e:
            messages.error(request, f'Error al actualizar: {str(e)}')
    return redirect('lista_conductores')

def eliminar_conductor(request, id):
    conductor = get_object_or_404(TransporteConductor, id_transporte_conductor=id)
    try:
        conductor.delete()
        messages.success(request, 'Conductor eliminado')
    except Exception:
        messages.error(request, 'No se puede eliminar al conductor porque tiene traslados asociados')
    return redirect('lista_conductores')
