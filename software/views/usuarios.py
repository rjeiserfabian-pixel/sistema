from datetime import datetime
from decimal import Decimal
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, render
from software.models.UsuarioModel import Usuario
from software.models.TipousuarioModel import Tipousuario
from software.models.TipodocumentoModel import Tipodocumento
from software.models.TipoclienteModel import Tipocliente
from software.models.ProveedoresModel import Proveedor
from software.models.ModulosModel import Modulos
from software.models.empresaModel import Empresa
from software.models.empleadoModel import Empleado

from software.models.detalletipousuarioxmodulosModel import Detalletipousuarioxmodulos

from software.models.departamentosModel import Departamentos

from django.db import connection
from openpyxl import Workbook
from openpyxl.utils import get_column_letter

# Importar las utilidades de cifrado
from software.utils.encryption_utils import EncryptionManager, PasswordManager
import cloudinary.uploader


def usuarios(request):
    id2 = request.session.get('idtipousuario')
    if not id2:
        return HttpResponse("<h1>No tiene acceso señor</h1>")
    
    permisos = Detalletipousuarioxmodulos.objects.filter(idtipousuario=id2)
    
    # ✅ FILTRAR USUARIOS POR SUCURSAL
    idusuario = request.session.get('idusuario')
    id_sucursal = request.session.get('id_sucursal')
    es_admin = (id2 == 1)
    
    if es_admin and id_sucursal:
        # Admin ve usuarios de la sucursal seleccionada
        usuarios_db = Usuario.objects.filter(
            estado=1,
            id_sucursal_id=id_sucursal
        ).select_related('idtipousuario', 'id_sucursal', 'idempresa')  # ✅ Agregar idempresa
    elif not es_admin:
        # Usuario normal ve solo usuarios de su sucursal
        try:
            usuario_actual = Usuario.objects.get(idusuario=idusuario)
            usuarios_db = Usuario.objects.filter(
                estado=1,
                id_sucursal=usuario_actual.id_sucursal
            ).select_related('idtipousuario', 'id_sucursal', 'idempresa')  # ✅ Agregar idempresa
        except Usuario.DoesNotExist:
            usuarios_db = []
    else:
        # Admin sin sucursal seleccionada no ve nada
        usuarios_db = []
    
    # Descifrar nombres de usuario para mostrarlos en la vista
    usuarios = []
    for usuario in usuarios_db:
        usuario.correo_descifrado = EncryptionManager.decrypt_data(usuario.correo)
        usuarios.append(usuario)
    
    tipoUsuarios = Tipousuario.objects.filter(estado=1)
    
    data = {
        'usuarios': usuarios,
        'tipoUsuarios': tipoUsuarios,
        'permisos': permisos,
        'es_admin': es_admin,
    }
    return render(request, 'usuarios/usuarios.html', data)


def agregar(request):
    if request.method == "POST":
        try:
            nombreUsuario = request.POST.get('nombreUsuario2')
            correoUsuario = request.POST.get('correoUsuario2')
            contrasenaUsuario = request.POST.get('contrasenaUsuario2')
            tipoUsuario = request.POST.get('tipoUsuario2')
            celularUsuario = request.POST.get('celularUsuario2')
            dniUsuario = request.POST.get('dniUsuario2')
            gmailUsuario = request.POST.get('gmailUsuario2')

            # Validaciones básicas
            if not all([nombreUsuario, correoUsuario, contrasenaUsuario, tipoUsuario, celularUsuario, dniUsuario]):
                return JsonResponse({"error": "Todos los campos son requeridos"}, status=400)

            # ⭐ OBTENER SUCURSAL DEL USUARIO QUE CREA
            idusuario_session = request.session.get('idusuario')
            id_sucursal_session = request.session.get('id_sucursal')
            
            # Validar que tenga sucursal seleccionada
            if not id_sucursal_session:
                return JsonResponse({
                    "error": "Debe seleccionar una sucursal en el modal de configuración antes de crear usuarios."
                }, status=400)

            # ✅ OBTENER LA EMPRESA DE LA SUCURSAL
            try:
                from software.models.sucursalesModel import Sucursales
                sucursal = Sucursales.objects.get(id_sucursal=id_sucursal_session)
                id_empresa = sucursal.idempresa_id  # Obtener el ID de la empresa
            except Sucursales.DoesNotExist:
                return JsonResponse({
                    "error": "La sucursal seleccionada no existe."
                }, status=400)

            # Cifrar el nombre de usuario
            correo_cifrado = EncryptionManager.encrypt_data(correoUsuario)
            if not correo_cifrado:
                return JsonResponse({"error": "Error al cifrar el nombre de usuario"}, status=400)
            
            # Hashear la contraseña
            contrasena_hasheada = PasswordManager.hash_password(contrasenaUsuario)
            if not contrasena_hasheada:
                return JsonResponse({"error": "Error al procesar la contraseña"}, status=400)

            # Traer la instancia de tipo usuario
            getTipoUsuario = get_object_or_404(Tipousuario, idtipousuario=tipoUsuario)

            # ✅ Crear el usuario CON SUCURSAL Y EMPRESA
            usuario = Usuario.objects.create(
                nombrecompleto=nombreUsuario,
                correo=correo_cifrado,
                contrasena=contrasena_hasheada,
                idtipousuario=getTipoUsuario,
                celular=celularUsuario,
                dni=dniUsuario,
                gmail=gmailUsuario,
                id_sucursal_id=id_sucursal_session,  # ✅ ASIGNAR SUCURSAL
                idempresa_id=id_empresa,             # ✅ ASIGNAR EMPRESA
                estado=1,
                puede_gestionar_logistica=request.POST.get('puede_gestionar_logistica2') == 'on'
            )
            usuario.save()
            
            print(f"✅ USUARIO CREADO:")
            print(f"   - ID: {usuario.idusuario}")
            print(f"   - Nombre: {usuario.nombrecompleto}")
            print(f"   - Sucursal: {sucursal.nombre_sucursal}")
            print(f"   - Empresa ID: {id_empresa}")
            
            return JsonResponse({
                "message": "Usuario agregado exitosamente",
                "id": usuario.idusuario
            }, status=201)
            
        except Exception as e:
            import traceback
            traceback.print_exc()
            return JsonResponse({"error": f"Error al crear usuario: {str(e)}"}, status=400)

    return JsonResponse({"error": "Método no permitido"}, status=405)


def editar(request):
    if request.method == "POST":
        try:
            idUsuario = request.POST.get('idusuario')
            nombreUsuario = request.POST.get('nombreUsuario')
            correoUsuario = request.POST.get('correoUsuario')
            contrasenaUsuario = request.POST.get('contrasenaUsuario')
            tipoUsuario = request.POST.get('tipoUsuario')
            celularUsuario = request.POST.get('celularUsuario')
            dniUsuario = request.POST.get('dniUsuario')
            gmailUsuario = request.POST.get('gmailUsuario')

            # Validaciones básicas
            if not all([idUsuario, nombreUsuario, correoUsuario, tipoUsuario, celularUsuario, dniUsuario]):
                return JsonResponse({"error": "Todos los campos son requeridos"}, status=400)

            # Obtener el usuario existente
            usuario = get_object_or_404(Usuario, idusuario=idUsuario)
            
            # ⭐ VALIDACIÓN: Solo se puede editar usuarios de la misma sucursal
            id_sucursal_session = request.session.get('id_sucursal')
            if usuario.id_sucursal_id != id_sucursal_session:
                return JsonResponse({
                    "error": "No tiene permisos para editar este usuario de otra sucursal."
                }, status=403)
            
            # Traer la instancia de tipo usuario
            getTipoUsuario = get_object_or_404(Tipousuario, idtipousuario=tipoUsuario)

            # Actualizar campos básicos
            usuario.nombrecompleto = nombreUsuario
            usuario.idtipousuario = getTipoUsuario
            usuario.celular = celularUsuario
            usuario.dni = dniUsuario
            usuario.gmail = gmailUsuario
            usuario.puede_gestionar_logistica = request.POST.get('puede_gestionar_logistica') == 'on'
            # NO modificar id_sucursal ni idempresa - se mantienen los originales
            
            # Verificar si el usuario cambió
            correo_actual_descifrado = EncryptionManager.decrypt_data(usuario.correo)
            if correo_actual_descifrado != correoUsuario:
                # Cifrar el nuevo nombre de usuario
                correo_cifrado = EncryptionManager.encrypt_data(correoUsuario)
                if not correo_cifrado:
                    return JsonResponse({"error": "Error al cifrar el nombre de usuario"}, status=400)
                usuario.correo = correo_cifrado
            
            # Verificar si la contraseña cambió
            if contrasenaUsuario and not contrasenaUsuario.startswith('pbkdf2_'):
                contrasena_hasheada = PasswordManager.hash_password(contrasenaUsuario)
                if not contrasena_hasheada:
                    return JsonResponse({"error": "Error al procesar la contraseña"}, status=400)
                usuario.contrasena = contrasena_hasheada
            
            usuario.save()
            
            return JsonResponse({
                "message": "Usuario editado exitosamente",
                "id": usuario.idusuario
            }, status=200)
            
        except Exception as e:
            import traceback
            traceback.print_exc()
            return JsonResponse({"error": f"Error al editar usuario: {str(e)}"}, status=400)

    return JsonResponse({"error": "Método no permitido"}, status=405)


def eliminar(request, id):
    if request.method == "GET":
        try:
            usuario = get_object_or_404(Usuario, idusuario=id)
            usuario.estado = 0
            usuario.save()
            return JsonResponse({"message": "Usuario eliminado exitosamente"}, status=200)
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=400)

    return JsonResponse({"error": "Método no permitido"}, status=405)


def login_usuario(correo_plano, contrasena_plana):
    """
    Función auxiliar para validar el login de un usuario
    Args:
        correo_plano (str): Correo en texto plano
        contrasena_plana (str): Contraseña en texto plano
    Returns:
        Usuario o None
    """
    try:
        # Buscar todos los usuarios activos
        usuarios = Usuario.objects.filter(estado=1)
        
        for usuario in usuarios:
            # Descifrar el nombre de usuario de cada usuario
            correo_descifrado = EncryptionManager.decrypt_data(usuario.correo)
            
            # Si el usuario coincide, verificar la contraseña
            if correo_descifrado == correo_plano:
                if PasswordManager.verify_password(contrasena_plana, usuario.contrasena):
                    return usuario
        
        return None
    except Exception as e:
        print(f"Error en login: {e}")
        return None

def mi_perfil(request):
    idusuario = request.session.get('idusuario')
    if not idusuario:
        return HttpResponse("<h1>No tiene acceso</h1>")
    
    usuario = get_object_or_404(Usuario, idusuario=idusuario)
    usuario.correo_descifrado = EncryptionManager.decrypt_data(usuario.correo)
    
    data = {
        'usuario': usuario,
        'nombrecompleto': usuario.nombrecompleto,
    }
    return render(request, 'usuarios/perfil.html', data)

def actualizar_perfil(request):
    if request.method == "POST":
        try:
            idusuario = request.session.get('idusuario')
            nombre = request.POST.get('nombrecompleto')
            celular = request.POST.get('celular')
            gmail = request.POST.get('gmail')
            imagen = request.FILES.get('imagen_perfil')
            
            if not all([nombre, celular]):
                return JsonResponse({"error": "Todos los campos son requeridos"}, status=400)
            
            usuario = get_object_or_404(Usuario, idusuario=idusuario)
            usuario.nombrecompleto = nombre
            usuario.celular = celular
            usuario.gmail = gmail
            
            if imagen:
                # SUBIR A CLOUDINARY
                upload_result = cloudinary.uploader.upload(
                    imagen,
                    folder="usuarios/perfiles/",
                    resource_type='image',
                    public_id=f'user_{idusuario}',
                    overwrite=True,
                )
                usuario.imagen_perfil = upload_result['secure_url']
                
            usuario.save()
            
            # Actualizar nombre en sesión
            request.session['nombrecompleto'] = nombre
            
            return JsonResponse({"message": "Perfil actualizado correctamente"}, status=200)
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=400)
    return JsonResponse({"error": "Método no permitido"}, status=405)

def cambiar_contrasena(request):
    if request.method == "POST":
        try:
            idusuario = request.session.get('idusuario')
            actual = request.POST.get('password_actual')
            nueva = request.POST.get('password_nueva')
            confirmar = request.POST.get('password_confirmar')
            
            if not all([actual, nueva, confirmar]):
                return JsonResponse({"error": "Todos los campos son requeridos"}, status=400)
            
            if nueva != confirmar:
                return JsonResponse({"error": "Las contraseñas no coinciden"}, status=400)
            
            usuario = get_object_or_404(Usuario, idusuario=idusuario)
            
            # Verificar contraseña actual
            if not PasswordManager.verify_password(actual, usuario.contrasena):
                return JsonResponse({"error": "La contraseña actual es incorrecta"}, status=400)
            
            # Hashear y guardar nueva contraseña
            usuario.contrasena = PasswordManager.hash_password(nueva)
            usuario.save()
            
            return JsonResponse({"message": "Contraseña actualizada correctamente"}, status=200)
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=400)
    return JsonResponse({"error": "Método no permitido"}, status=405)