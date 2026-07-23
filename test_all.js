




  let itemIndex = 0;
  let total = 0;
  let totalConfiguracionCuotas = 0; // NUEVA: Para rastrear coherencia entre total y cuotas

  //DATOS PARA AUTOCOMPLETE
  const proveedoresData = [
    
    { id: 1, text: "1" },
    
  ];

  const vehiculosData = [
    
    { id: 1, text: "1" },
    
  ];

  const repuestosData = [
    
    { id: 1, text: "1 (1Sin Marca - 1Sin Modelo - 1Sin Categoría) - Cód: 1" },
    
  ];

  // ====== DATA AUTOCOMPLETE PARA REGISTRO RÁPIDO DE REPUESTOS ======
  const categoriasRepData = [
    
    { id: 1, text: "1" },
    
  ];
  const marcasRepData = [
    
    { id: 1, text: "1" },
    
  ];

  const garantiasRepData = [
    
    { id: 1, text: "1" },
    
  ];

  //FUNCIÓN AUTOCOMPLETE GENÉRICA
  function setupAutocomplete(inputId, resultsId, data, hiddenId) {
    const input = document.getElementById(inputId);
    const results = document.getElementById(resultsId);
    const hidden = document.getElementById(hiddenId);

    if (!input) return;

    input.addEventListener('input', function () {
      const value = this.value.toLowerCase();
      results.innerHTML = '';

      if (value.length < 1) {
        results.style.display = 'none';
        hidden.value = '';
        return;
      }

      const searchTerms = value.split(' ').filter(term => term.trim() !== '');

      const filtered = data.filter(item => {
        const itemText = item.text.toLowerCase();
        return searchTerms.every(term => itemText.includes(term));
      });

      if (filtered.length === 0) {
        results.innerHTML = '<div class="autocomplete-item no-results">No se encontraron resultados</div>';
        results.style.display = 'block';
        return;
      }

      filtered.forEach(item => {
        const div = document.createElement('div');
        div.className = 'autocomplete-item';
        div.textContent = item.text;
        div.addEventListener('click', function () {
          input.value = item.text;
          hidden.value = item.id;
          results.style.display = 'none';
        });
        results.appendChild(div);
      });

      results.style.display = 'block';
    });

    // Cerrar al hacer clic fuera
    document.addEventListener('click', function (e) {
      if (!input.contains(e.target) && !results.contains(e.target)) {
        const arrow = input.parentElement.querySelector('.autocomplete-arrow');
        if (arrow && !arrow.contains(e.target)) {
          results.style.display = 'none';
        }
      }
    });

    // Limpiar al cambiar
    input.addEventListener('focus', function () {
      if (this.value && !hidden.value) {
        this.value = '';
      }
    });
  }

  //FUNCIÓN PARA ABRIR/CERRAR CON LA FLECHA
  function toggleAutocomplete(inputId, resultsId) {
    const input = document.getElementById(inputId);
    const results = document.getElementById(resultsId);

    // Determinar qué datos usar según el input
    let data = [];
    let hiddenId = '';

    if (inputId === 'proveedor_search') {
      data = proveedoresData;
      hiddenId = 'proveedor_id';
    } else if (inputId === 'vehiculo_search') {
      data = vehiculosData;
      hiddenId = 'veh_nombre';
    } else if (inputId === 'repuesto_search') {
      data = repuestosData;
      hiddenId = 'rep_nombre';
    }

    // Si ya está abierto, cerrar
    if (results.style.display === 'block') {
      results.style.display = 'none';
      return;
    }

    // Mostrar todos los elementos
    results.innerHTML = '';
    data.forEach(item => {
      const div = document.createElement('div');
      div.className = 'autocomplete-item';
      div.textContent = item.text;
      div.addEventListener('click', function (e) {
        e.stopPropagation();
        input.value = item.text;
        document.getElementById(hiddenId).value = item.id;
        results.style.display = 'none';
      });
      results.appendChild(div);
    });

    results.style.display = 'block';
    input.focus();
  }

  //FUNCIÓN PARA CERRAR MODAL DE PROVEEDOR Y VOLVER AL MODAL DE COMPRA
  function cerrarModalProveedor() {
    const modalProveedor = bootstrap.Modal.getInstance(document.getElementById('modalAgregarProveedorCompra'));
    if (modalProveedor) {
      modalProveedor.hide();
    }

    // Limpiar formulario
    document.getElementById('formAgregarProveedorCompra').reset();
    limpiarCamposProveedor();

    // Reabrir modal de compra después de un momento
    setTimeout(() => {
      const modalCompra = new bootstrap.Modal(document.getElementById('modalAgregarCompra'));
      modalCompra.show();
    }, 300);
  }

  //FUNCIÓN PARA CONSULTAR DOCUMENTO EN TOKENPERU (DESDE COMPRAS)
  async function consultarDocumentoTokenPeruCompra(numero) {
    const alertCargando = $('#alertCargandoCompra');
    const alertError = $('#alertErrorCompra');
    const alertExito = $('#alertExitoCompra');

    // Validar longitud
    if (numero.length !== 8 && numero.length !== 11) {
      return;
    }

    // Mostrar loading
    alertCargando.removeClass('d-none');
    alertError.addClass('d-none');
    alertExito.addClass('d-none');

    try {
      const response = await fetch(`/api/autocompletar-proveedor/?numero=${numero}`);
      const data = await response.json();

      alertCargando.addClass('d-none');

      if (data.success) {
        // Autocompletar campos
        $('#razonsocialProveedorCompra').val(data.razonsocial).addClass('campo-autocompletado');
        $('#direccionProveedorCompra').val(data.direccion || '').addClass('campo-autocompletado');
        $('#nombreComercialProveedorCompra').val(data.nombre_comercial || '').addClass('campo-autocompletado');
        $('#departamentoProveedorCompra').val(data.departamento || '').addClass('campo-autocompletado');
        $('#provinciaProveedorCompra').val(data.provincia || '').addClass('campo-autocompletado');
        $('#distritoProveedorCompra').val(data.distrito || '').addClass('campo-autocompletado');
        $('#tipoEntidadProveedorCompra').val(data.id_tipo_entidad);

        if (data.tipo === 'RUC') {
          // Mostrar info SUNAT
          $('#infoRucCompra').removeClass('d-none');
          $('#estadoSunatCompra').text(data.estado || 'N/A')
            .removeClass('bg-success bg-danger')
            .addClass(data.estado === 'ACTIVO' ? 'bg-success' : 'bg-danger');
          $('#condicionSunatCompra').text(data.condicion || 'N/A');

          // Badge RUC
          $('#badgeTipoDocCompra').text('RUC').removeClass('bg-secondary bg-info').addClass('bg-info').show();

          // Validar estado
          if (data.estado !== 'ACTIVO') {
            alertExito.removeClass('d-none');
            $('#mensajeExitoCompra').html(`<strong>RUC encontrado:</strong> ${data.razonsocial}<br><small class="text-warning">⚠️ Advertencia: El RUC no está ACTIVO en SUNAT</small>`);
          } else {
            alertExito.removeClass('d-none');
            $('#mensajeExitoCompra').html(`<strong>RUC encontrado:</strong> ${data.razonsocial}`);
          }
        } else {
          // DNI
          $('#infoRucCompra').addClass('d-none');
          $('#badgeTipoDocCompra').text('DNI').removeClass('bg-secondary bg-info').addClass('bg-secondary').show();

          alertExito.removeClass('d-none');
          $('#mensajeExitoCompra').html(`<strong>DNI encontrado:</strong> ${data.razonsocial}`);
        }

        // Remover animación después de 600ms
        setTimeout(() => {
          $('.campo-autocompletado').removeClass('campo-autocompletado');
        }, 600);

      } else {
        // Error de API
        alertError.removeClass('d-none');
        $('#mensajeErrorCompra').text(data.error || 'No se encontró el documento');
        limpiarCamposProveedor();
      }
    } catch (error) {
      alertCargando.addClass('d-none');
      alertError.removeClass('d-none');
      $('#mensajeErrorCompra').text('Error de conexión. Intente nuevamente.');
      console.error('Error:', error);
    }
  }

  // Función para limpiar campos del proveedor
  function limpiarCamposProveedor() {
    $('#razonsocialProveedorCompra').val('');
    $('#nombreComercialProveedorCompra').val('');
    $('#direccionProveedorCompra').val('');
    $('#departamentoProveedorCompra').val('');
    $('#provinciaProveedorCompra').val('');
    $('#distritoProveedorCompra').val('');
    $('#infoRucCompra').addClass('d-none');
    $('#badgeTipoDocCompra').hide();
  }

  //INICIALIZAR EVENTOS DEL MODAL DE PROVEEDOR
  document.addEventListener('DOMContentLoaded', function () {

    // Inicializar la fecha base de cuotas a hoy si no tiene valor (hora local)
    const now = new Date();
    const todayLocal = now.getFullYear() + '-' + String(now.getMonth() + 1).padStart(2, '0') + '-' + String(now.getDate()).padStart(2, '0');
    const baseDateInput = document.getElementById('fecha_base_cuotas');
    if (baseDateInput && !baseDateInput.value) {
      baseDateInput.value = todayLocal;
    }

    // Detectar tipo de documento al escribir
    $('#numdocProveedorCompra').on('input', function () {
      const valor = this.value.replace(/[^0-9]/g, '');
      this.value = valor; // Solo números

      const badge = $('#badgeTipoDocCompra');
      if (valor.length === 8) {
        badge.text('DNI').removeClass('bg-info').addClass('bg-secondary').show();
        $('#tipoEntidadProveedorCompra').val(1);
      } else if (valor.length === 11) {
        badge.text('RUC').removeClass('bg-secondary').addClass('bg-info').show();
        $('#tipoEntidadProveedorCompra').val(6);
      } else {
        badge.hide();
      }
    });

    // Consultar al presionar Enter
    $('#numdocProveedorCompra').on('keypress', function (e) {
      if (e.which === 13) { // Enter
        e.preventDefault();
        const numero = $(this).val().trim();
        if (numero.length === 8 || numero.length === 11) {
          consultarDocumentoTokenPeruCompra(numero);
        }
      }
    });

    // Consultar al hacer clic en el botón
    $('#btnConsultarDocCompra').on('click', function () {
      const numero = $('#numdocProveedorCompra').val().trim();
      if (numero.length === 8 || numero.length === 11) {
        consultarDocumentoTokenPeruCompra(numero);
      } else {
        Swal.fire({
          title: 'Documento inválido',
          text: 'Ingrese un DNI (8 dígitos) o RUC (11 dígitos)',
          icon: 'warning',
          confirmButtonText: 'OK'
        });
      }
    });

    //GUARDAR NUEVO PROVEEDOR
    $('#btnGuardarProveedorCompra').on('click', function () {
      const form = $('#formAgregarProveedorCompra')[0];

      // Validar formulario
      if (!form.checkValidity()) {
        form.reportValidity();
        return;
      }

      // Mostrar loading
      Swal.fire({
        title: 'Guardando proveedor...',
        allowOutsideClick: false,
        allowEscapeKey: false,
        showConfirmButton: false,
        willOpen: () => {
          Swal.showLoading();
        }
      });

      const formData = new FormData(form);

      $.ajax({
        type: "POST",
        url: "",
        data: formData,
        processData: false,
        contentType: false,
        success: function (response) {
          Swal.close();

          // Obtener datos del proveedor recién creado
          const numdoc = $('#numdocProveedorCompra').val();
          const razonsocial = $('#razonsocialProveedorCompra').val();

          Swal.fire({
            title: '¡Proveedor guardado!',
            text: 'El proveedor se ha registrado correctamente',
            icon: 'success',
            timer: 2000,
            showConfirmButton: false
          }).then(() => {
            // Cerrar modal de proveedor
            const modalProveedor = bootstrap.Modal.getInstance(document.getElementById('modalAgregarProveedorCompra'));
            if (modalProveedor) {
              modalProveedor.hide();
            }

            //ACTUALIZAR LA LISTA DE PROVEEDORES Y SELECCIONAR EL NUEVO
            // Agregar el nuevo proveedor al array de datos
            $.ajax({
              url: '/api/obtener-ultimo-proveedor/',  // Necesitarás crear este endpoint
              method: 'GET',
              success: function (nuevoProveedor) {
                // Agregar al array de datos
                proveedoresData.push({
                  id: nuevoProveedor.id,
                  text: nuevoProveedor.razonsocial
                });

                // Seleccionar automáticamente el nuevo proveedor
                $('#proveedor_search').val(nuevoProveedor.razonsocial);
                $('#proveedor_id').val(nuevoProveedor.id);

                // Reabrir modal de compra
                setTimeout(() => {
                  const modalCompra = new bootstrap.Modal(document.getElementById('modalAgregarCompra'));
                  modalCompra.show();
                }, 300);
              },
              error: function () {
                // Si falla, refrescar la página para actualizar los datos
                window.location.reload();
              }
            });
          });
        },
        error: function (xhr) {
          Swal.fire({
            title: 'Error al guardar',
            text: xhr.responseText || 'Ocurrió un error al guardar el proveedor',
            icon: 'error',
            confirmButtonText: 'OK'
          });
        }
      });
    });
  });

  //INICIALIZAR AUTOCOMPLETES
  document.addEventListener('DOMContentLoaded', function () {
    setupAutocomplete('proveedor_search', 'proveedor_results', proveedoresData, 'proveedor_id');
    setupAutocomplete('vehiculo_search', 'vehiculo_results', vehiculosData, 'veh_nombre');
    setupAutocomplete('repuesto_search', 'repuesto_results', repuestosData, 'rep_nombre');
  });

  document.getElementById("tipo_item").addEventListener("change", function () {
    const tipo = this.value;
    const cantidadInput = document.getElementById("cantidad");
    if (tipo === "vehiculo") {
      document.getElementById("formVehiculo").style.display = "block";
      document.getElementById("formRepuesto").style.display = "none";
      cantidadInput.value = "1";
      cantidadInput.readOnly = true;
    } else if (tipo === "repuesto") {
      document.getElementById("formVehiculo").style.display = "none";
      document.getElementById("formRepuesto").style.display = "block";
      cantidadInput.readOnly = false;
    } else {
      document.getElementById("formVehiculo").style.display = "none";
      document.getElementById("formRepuesto").style.display = "none";
      cantidadInput.readOnly = false;
    }
  });

  function calcularPreciosVenta() {
    calcularPrecioDesdeMargen('minimo');
    calcularPrecioDesdeMargen('maximo');
  }

  function calcularPrecioDesdeMargen(tipo) {
    const precioCompra = parseFloat(document.getElementById("precio_compra").value) || 0;
    const margen = parseFloat(document.getElementById(`margen_${tipo}`).value) || 0;
    if (precioCompra > 0) {
      const precioFinal = precioCompra * (1 + (margen / 100));
      document.getElementById(`precio_${tipo}`).value = precioFinal.toFixed(2);
    } else {
      document.getElementById(`precio_${tipo}`).value = "";
    }
  }

  function calcularMargenDesdePrecio(tipo) {
    const precioCompra = parseFloat(document.getElementById("precio_compra").value) || 0;
    const precioFinal = parseFloat(document.getElementById(`precio_${tipo}`).value) || 0;
    if (precioCompra > 0 && precioFinal > 0) {
      const margen = ((precioFinal / precioCompra) - 1) * 100;
      document.getElementById(`margen_${tipo}`).value = margen.toFixed(2);
    } else {
      document.getElementById(`margen_${tipo}`).value = "";
    }
  }

  async function agregarDetalle() {
    const tipo = document.getElementById("tipo_item").value;
    const cantidad = parseInt(document.getElementById("cantidad").value) || 0;
    const precioCompra = parseFloat(document.getElementById("precio_compra").value) || 0;
    const precioMinimo = parseFloat(document.getElementById("precio_minimo").value) || 0;
    const precioMaximo = parseFloat(document.getElementById("precio_maximo").value) || 0;
    const margenMinimo = parseFloat(document.getElementById("margen_minimo").value) || 0;
    const margenMaximo = parseFloat(document.getElementById("margen_maximo").value) || 0;

    if (!tipo || cantidad <= 0 || precioCompra <= 0 || precioMinimo <= 0 || precioMaximo <= 0) {
      Swal.fire("Campos incompletos", "Debes llenar todos los campos del detalle.", "warning");
      return;
    }

    if (precioMinimo > precioMaximo) {
      Swal.fire("Error", "El Precio Mínimo no puede ser mayor al Precio Máximo.", "warning");
      return;
    }

    itemIndex++;
    document.getElementById("items_count").value = itemIndex;

    let nombre = "";
    let extraInputs = "";

    if (tipo === "vehiculo") {
      const idProducto = document.getElementById("veh_nombre").value;
      const vehiculoInput = document.getElementById("vehiculo_search");

      if (!idProducto) {
        Swal.fire("Error", "Debe seleccionar un producto", "warning");
        itemIndex--;
        document.getElementById("items_count").value = itemIndex;
        return;
      }

      nombre = vehiculoInput.value;
      const serieMotor = document.getElementById("veh_motor").value.trim();
      const serieChasis = document.getElementById("veh_chasis").value.trim();
      const anio = document.getElementById("veh_anio").value.trim();
      const estadoProd = document.getElementById("veh_estado").value;
      const imperfecciones = document.getElementById("veh_imperfecciones").value.trim();
      const placas = document.getElementById("veh_placas").value.trim();

      if (!serieMotor) {
        Swal.fire("Error", "Debe ingresar la serie del motor", "warning");
        itemIndex--;
        document.getElementById("items_count").value = itemIndex;
        return;
      }

      if (!serieChasis) {
        Swal.fire("Error", "Debe ingresar la serie del chasis", "warning");
        itemIndex--;
        document.getElementById("items_count").value = itemIndex;
        return;
      }

      if (!anio) {
        Swal.fire("Error", "Debe ingresar el año del vehículo", "warning");
        itemIndex--;
        document.getElementById("items_count").value = itemIndex;
        return;
      }

      if (!estadoProd) {
        Swal.fire("Error", "Debe seleccionar el estado del producto", "warning");
        itemIndex--;
        document.getElementById("items_count").value = itemIndex;
        return;
      }

      if (estadoProd === "2" && !placas) {
        Swal.fire("Error", "Debe ingresar las placas para un vehículo semi-nuevo", "warning");
        itemIndex--;
        document.getElementById("items_count").value = itemIndex;
        return;
      }

      // Validación LOCAL (contra la tabla actual)
      let existeEnTabla = false;
      const inputsMotor = document.querySelectorAll('input[name^="serie_motor_"]');
      const inputsChasis = document.querySelectorAll('input[name^="serie_chasis_"]');
      
      for (let i = 0; i < inputsMotor.length; i++) {
        if (inputsMotor[i].value === serieMotor || inputsChasis[i].value === serieChasis) {
          existeEnTabla = true;
          break;
        }
      }
      
      if (existeEnTabla) {
        Swal.fire("Error", "Esta Serie Motor o Serie Chasis ya fue agregada a la lista de abajo.", "warning");
        itemIndex--;
        document.getElementById("items_count").value = itemIndex;
        return;
      }
      
      // Validación BASE DE DATOS
      try {
        const response = await fetch(`/api/compras/validar-series/?motor=${encodeURIComponent(serieMotor)}&chasis=${encodeURIComponent(serieChasis)}`);
        const data = await response.json();
        
        if (data.existe) {
          Swal.fire("Error", data.mensaje, "warning");
          itemIndex--;
          document.getElementById("items_count").value = itemIndex;
          return;
        }
      } catch (error) {
        console.error("Error al validar las series:", error);
        Swal.fire("Error", "Ocurrió un error al validar la serie en el servidor.", "error");
        itemIndex--;
        document.getElementById("items_count").value = itemIndex;
        return;
      }

      extraInputs = `
      <input type="hidden" name="idproducto_${itemIndex}" value="${idProducto}">
      <input type="hidden" name="serie_motor_${itemIndex}" value="${serieMotor}">
      <input type="hidden" name="serie_chasis_${itemIndex}" value="${serieChasis}">
      <input type="hidden" name="anio_${itemIndex}" value="${anio}">
      <input type="hidden" name="idestadoproducto_${itemIndex}" value="${estadoProd}">
      <input type="hidden" name="imperfecciones_${itemIndex}" value="${imperfecciones}">
      <input type="hidden" name="placas_${itemIndex}" value="${placas}">
    `;

      vehiculoInput.value = "";
      document.getElementById("veh_nombre").value = "";
      document.getElementById("veh_motor").value = "";
      document.getElementById("veh_chasis").value = "";
      document.getElementById("veh_anio").value = "";
      document.getElementById("veh_estado").value = "";
      document.getElementById("veh_imperfecciones").value = "";
      document.getElementById("veh_placas").value = "";

    } else if (tipo === "repuesto") {
      const idRepuesto = document.getElementById("rep_nombre").value;
      const repuestoInput = document.getElementById("repuesto_search");

      if (!idRepuesto) {
        Swal.fire("Error", "Debe seleccionar un repuesto", "warning");
        itemIndex--;
        document.getElementById("items_count").value = itemIndex;
        return;
      }

      nombre = repuestoInput.value;
      const descripcionLibre = document.getElementById("rep_ubicacion").value.trim();


      extraInputs = `
      <input type="hidden" name="id_repuesto_${itemIndex}" value="${idRepuesto}">
      <input type="hidden" name="descripcion_${itemIndex}" value="${descripcionLibre}">
    `;

      repuestoInput.value = "";
      document.getElementById("rep_nombre").value = "";
      document.getElementById("rep_ubicacion").value = "";
    }

    const subtotal = cantidad * precioCompra;
    total += subtotal;

    const fila = `
    <tr id="fila_${itemIndex}">
      <td>${tipo}</td>
      <td>${nombre}</td>
      <td style="width: 100px;">
        <input type="number" name="cantidad_${itemIndex}" id="fila_cantidad_${itemIndex}" class="form-control form-control-sm text-end" value="${cantidad}" min="1" onchange="recalcularFilaCompra(${itemIndex})">
      </td>
      <td style="width: 130px;">
        <input type="number" name="precio_compra_${itemIndex}" id="fila_precio_compra_${itemIndex}" class="form-control form-control-sm text-end" value="${precioCompra.toFixed(2)}" step="0.01" min="0" onchange="recalcularFilaCompra(${itemIndex})">
      </td>
      <td style="width: 130px;">
        <input type="number" name="precio_minimo_${itemIndex}" id="fila_precio_minimo_${itemIndex}" class="form-control form-control-sm text-end" value="${precioMinimo.toFixed(2)}" step="0.01" min="0">
      </td>
      <td style="width: 130px;">
        <input type="number" name="precio_maximo_${itemIndex}" id="fila_precio_maximo_${itemIndex}" class="form-control form-control-sm text-end" value="${precioMaximo.toFixed(2)}" step="0.01" min="0">
      </td>
      <td id="fila_subtotal_${itemIndex}" class="text-end fw-bold">${subtotal.toFixed(2)}</td>
      <td>
        <button type="button" class="btn btn-danger btn-sm" onclick="eliminarDetalle(${itemIndex})"><i class="fa-solid fa-trash"></i></button>
      </td>
      <td style="display:none">
        <input type="hidden" name="idcompradetalle_${itemIndex}" value="">
        <input type="hidden" name="tipo_item_${itemIndex}" value="${tipo}">
        <input type="hidden" name="margen_minimo_${itemIndex}" value="${margenMinimo.toFixed(2)}">
        <input type="hidden" name="margen_maximo_${itemIndex}" value="${margenMaximo.toFixed(2)}">
        ${extraInputs}
      </td>
    </tr>
  `;

    document.querySelector("#tablaDetalles").insertAdjacentHTML("beforeend", fila);
    document.getElementById("totalGeneral").innerText = total.toFixed(2);

    document.getElementById("cantidad").value = "1";
    document.getElementById("cantidad").readOnly = false;
    document.getElementById("precio_compra").value = "";
    document.getElementById("precio_minimo").value = "";
    document.getElementById("precio_maximo").value = "";
    document.getElementById("margen_minimo").value = "";
    document.getElementById("margen_maximo").value = "";
    document.getElementById("tipo_item").value = "";

    document.getElementById("formVehiculo").style.display = "none";
    document.getElementById("formRepuesto").style.display = "none";
  }

  function recalcularFilaCompra(index) {
    const cant = parseFloat($(`#fila_cantidad_${index}`).val()) || 0;
    const precioComp = parseFloat($(`#fila_precio_compra_${index}`).val()) || 0;
    const nuevoSub = cant * precioComp;
    $(`#fila_subtotal_${index}`).text(nuevoSub.toFixed(2));
    recalcularTotalGeneralCompra();
  }

  function recalcularTotalGeneralCompra() {
    let nuevoTotal = 0;
    $('#tablaDetalles tr').each(function() {
      const idx = this.id.split('_')[1];
      if (idx) {
        const cant = parseFloat($(`#fila_cantidad_${idx}`).val()) || 0;
        const precioComp = parseFloat($(`#fila_precio_compra_${idx}`).val()) || 0;
        nuevoTotal += (cant * precioComp);
      }
    });
    total = nuevoTotal; // Actualizamos la global
    $('#totalGeneral').text(total.toFixed(2));
  }

  function eliminarDetalle(index) {
    const fila = document.getElementById(`fila_${index}`);
    if (fila) fila.remove();
    recalcularTotalGeneralCompra();
  }

  //VALIDACIÓN JAVASCRIPT: Verificar sucursal principal
  const esSucursalPrincipal = 1;

  //NUEVO: Guardar compra con verificación de caja
  $("#guardarCompra").click(function (e) {
    e.preventDefault();

    //VERIFICAR SI ES SUCURSAL PRINCIPAL
    if (!esSucursalPrincipal) {
      Swal.fire({
        icon: 'error',
        title: 'Acceso Denegado',
        text: 'Solo la sucursal principal puede realizar compras.',
        confirmButtonColor: '#dc3545'
      });
      return;
    }

    //VERIFICAR CAJA ANTES DE TODO (Solo si afecta caja)
    const tieneCajaAbierta = 1;
    const afectaCaja = $('#afecta_caja').val() === '1';

  if (!tieneCajaAbierta && afectaCaja) {
    Swal.fire({
      icon: 'warning',
      title: 'Caja Requerida',
      html: `<p>Debe aperturar una caja antes de realizar compras.</p>
             <p class="text-muted mt-2"><small>Haga clic en "Aperturar Caja" para abrir el formulario de apertura.</small></p>`,
      showCancelButton: true,
      confirmButtonText: '<i class="bi bi-box-arrow-in-right"></i> Aperturar Caja',
      cancelButtonText: 'Cancelar',
      confirmButtonColor: '#0d9488',
      cancelButtonColor: '#6c757d'
    }).then((result) => {
      if (result.isConfirmed) {
        // Cerrar modal de compra
        const modalCompra = bootstrap.Modal.getInstance(document.getElementById('modalAgregarCompra'));
        if (modalCompra) {
          modalCompra.hide();
        }

        // Abrir modal de gestión de caja
        setTimeout(() => {
          const modalCaja = new bootstrap.Modal(document.getElementById('modalGestionCaja'));
          modalCaja.show();
        }, 300);
      }
    });
    return;
  }

  const formaPago = document.getElementById("forma_pago").value;
  const proveedorId = document.getElementById("proveedor_id").value;
  const tipoCliente = document.querySelector('select[name="tipo_cliente"]').value;
  const numCorrelativo = document.querySelector('input[name="numcorrelativo"]').value.trim();
  const fechaCompra = document.querySelector('input[name="fechacompra"]').value;

  if (!proveedorId) {
    Swal.fire({
      title: 'Campo requerido',
      text: 'Debe seleccionar un proveedor.',
      icon: 'warning',
      confirmButtonText: 'OK'
    });
    return;
  }
  if (!formaPago) {
    Swal.fire({
      title: 'Campo requerido',
      text: 'Debe seleccionar una forma de pago.',
      icon: 'warning',
      confirmButtonText: 'OK'
    });
    return;
  }
  if (!tipoCliente) {
    Swal.fire({
      title: 'Campo requerido',
      text: 'Debe seleccionar un tipo de comprobante.',
      icon: 'warning',
      confirmButtonText: 'OK'
    });
    return;
  }
  if (!numCorrelativo) {
    Swal.fire({
      title: 'Campo requerido',
      text: 'El número correlativo es obligatorio.',
      icon: 'warning',
      confirmButtonText: 'OK'
    });
    return;
  }
  if (numCorrelativo.length > 25) {
    Swal.fire({
      title: 'Dato inválido',
      text: 'El número correlativo no puede exceder 25 caracteres.',
      icon: 'warning',
      confirmButtonText: 'OK'
    });
    return;
  }
  if (!fechaCompra) {
    Swal.fire({
      title: 'Campo requerido',
      text: 'La fecha de compra es obligatoria.',
      icon: 'warning',
      confirmButtonText: 'OK'
    });
    return;
  }
  if (formaPago !== "2") {
    const filas = document.querySelectorAll('.select-tipo-pago-compra');
    if (filas.length === 0) {
        Swal.fire({
          title: 'Campo requerido',
          text: 'Debe registrar al menos un método de pago.',
          icon: 'warning',
          confirmButtonText: 'OK'
        });
        return;
    }
    let allOk = true;
    filas.forEach(sel => { if (!sel.value) allOk = false; });
    if (!allOk) {
        Swal.fire({
          title: 'Campo requerido',
          text: 'Seleccione el método en todas las filas de pago.',
          icon: 'warning',
          confirmButtonText: 'OK'
        });
        return;
    }
    
    let opOk = true;
    document.querySelectorAll('.pago-row-compra').forEach(row => {
        const container = row.querySelector('.nro-op-compra-container');
        if (!container.classList.contains('d-none')) {
            const inp = container.querySelector('input');
            if (!inp.value.trim()) opOk = false;
        }
    });
    if (!opOk) {
        Swal.fire({
          title: 'Campo requerido',
          text: 'El N° de Operación es obligatorio para el método de pago seleccionado.',
          icon: 'warning',
          confirmButtonText: 'OK'
        });
        return;
    }

    if (filas.length > 1) {
        let multipleId = '';
        for (let opt of filas[0].options) {
            if (opt.textContent.trim().toLowerCase().includes('múltipl') || opt.textContent.trim().toLowerCase().includes('multipl')) {
                multipleId = opt.value; break;
            }
        }
        document.getElementById('tipo_pago_hidden_compra').value = multipleId || filas[0].value;
    } else {
        document.getElementById('tipo_pago_hidden_compra').value = filas[0].value;
    }
  }

  const tieneCuotas = document.getElementById("tiene_cuotas").value;

  if (formaPago === "2" && tieneCuotas === "0") {
    Swal.fire({
      title: "Cuotas no configuradas",
      text: "Debe configurar las cuotas para compras a crédito antes de guardar",
      icon: "warning",
      confirmButtonColor: "#f0ad4e"
    });
    return;
  }

  // VALIDACIÓN DE COHERENCIA: Total Compra vs Total Configurado en Cuotas
  if (formaPago === "2" && Math.abs(total - totalConfiguracionCuotas) > 0.01) {
    Swal.fire({
      title: "Total desactualizado",
      text: "El total de la compra ha cambiado (" + total.toFixed(2) + "). Por favor entre al botón 'Configurar Cuotas' para actualizar el plan de pagos.",
      icon: "warning",
      confirmButtonColor: "#f0ad4e"
    });
    return;
  }

  const itemsCount = parseInt(document.getElementById("items_count").value) || 0;
  if (itemsCount === 0) {
    Swal.fire({
      title: "Sin productos",
      text: "Debe agregar al menos un producto a la compra",
      icon: "warning",
      confirmButtonColor: "#f0ad4e"
    });
    return;
  }

  // Mostrar loading
  Swal.fire({
    text: 'Por favor espere',
    allowOutsideClick: false,
    allowEscapeKey: false,
    showConfirmButton: false,
    willOpen: () => {
      Swal.showLoading();
    }
  });

  let form = $("#formCompra");
  let formData = new FormData(form[0]);

  $.ajax({
    type: "POST",
    url: form.attr("action"),
    data: formData,
    processData: false,
    contentType: false,
    success: function (res) {
      if (res.ok) {
        Swal.fire({
          title: "Éxito",
          text: res.message || "Operación completada.",
          icon: "success",
          confirmButtonColor: "#198754"
        }).then(() => {
          window.location.href = "";
        });
      } else {
        //VERIFICAR SI EL ERROR ES POR FALTA DE CAJA
        if (res.necesita_aperturar || res.codigo === 'CAJA_REQUERIDA') {
          Swal.fire({
            icon: 'warning',
            title: 'Caja Requerida',
            text: res.error || 'Debe aperturar una caja antes de realizar compras',
            showCancelButton: true,
            confirmButtonText: '<i class="bi bi-box-arrow-in-right"></i> Aperturar Caja',
            cancelButtonText: 'Cancelar',
            confirmButtonColor: '#0d9488',
            cancelButtonColor: '#6c757d'
          }).then((result) => {
            if (result.isConfirmed) {
              // Cerrar modal de compra
              const modalCompra = bootstrap.Modal.getInstance(document.getElementById('modalAgregarCompra'));
              if (modalCompra) {
                modalCompra.hide();
              }

              // Abrir modal de gestión de caja
              setTimeout(() => {
                const modalCaja = new bootstrap.Modal(document.getElementById('modalGestionCaja'));
                modalCaja.show();
              }, 300);
            }
          });
        } else {
          Swal.fire({
            title: "Error",
            text: res.error || "Error desconocido",
            icon: "error",
            confirmButtonText: "OK"
          });
        }
      }
    },
    error: function (xhr) {
      console.log("Error AJAX:", xhr);

      let errorMessage = "Ocurrió un problema al guardar la compra.";
      let necesitaAperturar = false;

      if (xhr.responseJSON && xhr.responseJSON.error) {
        errorMessage = xhr.responseJSON.error;
        necesitaAperturar = xhr.responseJSON.necesita_aperturar || false;
      } else {
        try {
          const response = JSON.parse(xhr.responseText);
          errorMessage = response.error || errorMessage;
          necesitaAperturar = response.necesita_aperturar || false;
        } catch (e) {
          if (xhr.responseText) {
            errorMessage = xhr.responseText;
          }
        }
      }

      //VERIFICAR SI EL ERROR ES POR FALTA DE CAJA
      if (necesitaAperturar) {
        Swal.fire({
          icon: 'warning',
          title: 'Caja Requerida',
          text: errorMessage,
          showCancelButton: true,
          confirmButtonText: '<i class="bi bi-box-arrow-in-right"></i> Aperturar Caja',
          cancelButtonText: 'Cancelar',
          confirmButtonColor: '#0d9488',
          cancelButtonColor: '#6c757d'
        }).then((result) => {
          if (result.isConfirmed) {
            const modalCompra = bootstrap.Modal.getInstance(document.getElementById('modalAgregarCompra'));
            if (modalCompra) {
              modalCompra.hide();
            }

            setTimeout(() => {
              const modalCaja = new bootstrap.Modal(document.getElementById('modalGestionCaja'));
              modalCaja.show();
            }, 300);
          }
        });
      } else {
        Swal.fire({
          title: "Error",
          text: errorMessage,
          icon: "error",
          confirmButtonText: "OK"
        });
      }
    }
  });
});

  //Resto de eventos DOM
  document.addEventListener("DOMContentLoaded", function () {
    const estadoSelect = document.getElementById("veh_estado");
    const imperfeccionesContainer = document.getElementById("veh_imperfecciones_container");
    const placasContainer = document.getElementById("veh_placas_container");
    const imperfeccionesField = document.getElementById("veh_imperfecciones");
    const placasField = document.getElementById("veh_placas");

    function toggleImperfecciones() {
      const selectedValue = estadoSelect.value;
      if (selectedValue === "2") {
        imperfeccionesContainer.style.display = "block";
        placasContainer.style.display = "block";
        imperfeccionesField.required = true;
        placasField.required = true;
      } else {
        imperfeccionesContainer.style.display = "none";
        placasContainer.style.display = "none";
        imperfeccionesField.required = false;
        placasField.required = false;
        imperfeccionesField.value = "";
        placasField.value = "";
      }
    }

    toggleImperfecciones();
    estadoSelect.addEventListener("change", toggleImperfecciones);
  });

  document.addEventListener("DOMContentLoaded", function () {
    const formaPago = document.getElementById("forma_pago");
    const btnCuotasContainer = document.getElementById("btn_cuotas_container");
    const seccionMetodosPago = document.getElementById("seccion_metodos_pago_compra");

    formaPago.addEventListener("change", function () {
      if (this.value == "2") {
        seccionMetodosPago.classList.add("d-none");
        btnCuotasContainer.classList.remove("d-none");
      } else {
        seccionMetodosPago.classList.remove("d-none");
        btnCuotasContainer.classList.add("d-none");
        document.getElementById("tiene_cuotas").value = "0";
        document.querySelectorAll(".cuota-hidden").forEach(e => e.remove());
        if (document.querySelectorAll('.pago-row-compra').length === 0) {
            agregarFilaPagoCompra();
        }
      }
    });

    const tipoPeriodo = document.getElementById("tipo_periodo");
    const containerDias = document.getElementById("container_dias");
    const containerMeses = document.getElementById("container_meses");

    tipoPeriodo.addEventListener("change", function () {
      if (this.value === "meses") {
        containerDias.classList.add("d-none");
        containerMeses.classList.remove("d-none");
      } else {
        containerDias.classList.remove("d-none");
        containerMeses.classList.add("d-none");
      }
    });
  });

  // NUEVA: Función para abrir el modal de compra nueva (limpiando todo)
  function abrirNuevaCompra() {
    limpiarFormularioCompra();
    const modalCompra = new bootstrap.Modal(document.getElementById('modalAgregarCompra'));
    modalCompra.show();
  }

  // NUEVA: Función dedicada a limpiar el formulario
  function limpiarFormularioCompra() {
    $('#formCompra').attr('action', "");
    $('#modalAgregarCompra .modal-title').text('Nueva Compra');
    $('#guardarCompra').text('Guardar Compra');
    resetearPagosCompra();
    $('#formCompra')[0].reset();
    $('#formVehiculo').hide();
    $('#formRepuesto').hide();
    $('#tablaDetalles').html('');
    itemIndex = 0;
    total = 0;
    $('#totalGeneral').text('0.00');
    $('#items_count').val('0');
    $('.cuota-hidden').remove();
    $('#tiene_cuotas').val('0');
    totalConfiguracionCuotas = 0;

    // Restaurar Forma de Pago
    $('#forma_pago').prop('disabled', false);
    $('#forma_pago_hidden').remove();
    
    // Limpiar tabla de cuotas en el modal
    document.getElementById('tablaCuotas').innerHTML = '';
    const resumen = document.getElementById('resumenCuotasCompra');
    if (resumen) resumen.innerHTML = '';
  }


  //FUNCIÓN GENERAR CUOTAS
  function generarCuotas() {
    //OBTENER VALORES
    const totalCompra = parseFloat(document.getElementById("totalGeneral").innerText) || 0;
    const cantidadCuotas = parseInt(document.getElementById("credito_cuotas").value) || 0;
    const tasaInteres = parseFloat(document.getElementById("credito_tasa").value) || 0;
    const montoAdelanto = parseFloat(document.getElementById("monto_adelanto").value) || 0;
    const tipoPeriodo = document.getElementById("tipo_periodo").value;

    //VALIDACIONES
    if (totalCompra === 0) {
      Swal.fire({
        icon: 'warning',
        title: 'Total requerido',
        text: 'Debe agregar productos antes de configurar las cuotas',
        confirmButtonColor: '#ffc107'
      });
      return;
    }

    if (cantidadCuotas < 1 || cantidadCuotas > 36) {
      Swal.fire({
        icon: 'warning',
        title: 'Cantidad inválida',
        text: 'La cantidad de cuotas debe estar entre 1 y 36',
        confirmButtonColor: '#ffc107'
      });
      return;
    }

    if (montoAdelanto >= totalCompra) {
      Swal.fire({
        icon: 'warning',
        title: 'Adelanto inválido',
        text: 'El monto del adelanto debe ser menor al total de la compra',
        confirmButtonColor: '#ffc107'
      });
      return;
    }

    //CALCULAR MONTO A FINANCIAR
    const montoFinanciar = totalCompra - montoAdelanto;

    //CALCULAR MONTO POR CUOTA (sin interés)
    const montoCuotaBase = montoFinanciar / cantidadCuotas;

    //CALCULAR INTERÉS POR CUOTA
    const tasaDecimal = tasaInteres / 100;
    const interesCuota = montoCuotaBase * tasaDecimal;

    //TOTAL POR CUOTA (capital + interés)
    const totalCuota = montoCuotaBase + interesCuota;

    //GENERAR FECHAS
    const fechas = [];
    let baseDay = 1;
    let fechaBaseVal = document.getElementById('fecha_base_cuotas').value;
    let fechaActual = new Date();

    if (fechaBaseVal) {
      const partes = fechaBaseVal.split('-');
      fechaActual = new Date(partes[0], partes[1] - 1, partes[2]);
      baseDay = fechaActual.getDate();
    } else {
      baseDay = fechaActual.getDate();
    }

    //GENERAR TABLA DE CUOTAS
    let tablaCuotas = '';
    let totalFinanciado = 0;
    let totalIntereses = 0;

    //LIMPIAR CUOTAS ANTERIORES
    document.querySelectorAll('.cuota-hidden').forEach(e => e.remove());

    for (let i = 1; i <= cantidadCuotas; i++) {
      const fechaVencimiento = new Date(fechaActual);
      const fechaISO = fechaVencimiento.toISOString().split('T')[0];
      const fechaFormateada = formatearFecha(fechaVencimiento);

      totalFinanciado += montoCuotaBase;
      totalIntereses += interesCuota;

      //AGREGAR FILA A LA TABLA
      tablaCuotas += `
      <tr>
        <td class="text-center"><strong>Cuota ${i}</strong></td>
        <td class="text-center">
          <input type="date" 
                 id="fecha_cuota_visual_${i}"
                 class="form-control form-control-sm fecha-cuota-editable" 
                 value="${fechaISO}" 
                 data-cuota="${i}"
                 onchange="actualizarFechaCuota(${i})">
        </td>
        <td class="text-end">S/ ${montoCuotaBase.toFixed(2)}</td>
        <td class="text-end ${tasaInteres > 0 ? 'text-danger' : ''}">S/ ${interesCuota.toFixed(2)}</td>
        <td class="text-end fw-bold text-success">S/ ${totalCuota.toFixed(2)}</td>
      </tr>
    `;

      //AGREGAR INPUTS OCULTOS CON LA FECHA
      const adelantoRegistro = (i === 1) ? montoAdelanto : 0;

      document.getElementById("formCompra").insertAdjacentHTML("beforeend", `
      <input type="hidden" class="cuota-hidden" name="numero_cuota_${i}" value="${i}">
      <input type="hidden" class="cuota-hidden" name="monto_${i}" value="${montoCuotaBase.toFixed(2)}">
      <input type="hidden" class="cuota-hidden" name="tasa_${i}" value="${tasaInteres.toFixed(2)}">
      <input type="hidden" class="cuota-hidden" name="interes_${i}" value="${interesCuota.toFixed(2)}">
      <input type="hidden" class="cuota-hidden" name="total_${i}" value="${totalCuota.toFixed(2)}">
      <input type="hidden" class="cuota-hidden" id="fecha_vencimiento_${i}" name="fecha_vencimiento_${i}" value="${fechaISO}">
      <input type="hidden" class="cuota-hidden" name="monto_adelanto_${i}" value="${adelantoRegistro.toFixed(2)}">
    `);

      //CALCULAR SIGUIENTE FECHA
      if (tipoPeriodo === 'meses') {
        let currentMonth = fechaActual.getMonth();
        let currentYear = fechaActual.getFullYear();
        let nextMonth = currentMonth + 1;
        
        let lastDayOfNextMonth = new Date(currentYear, nextMonth + 1, 0).getDate();
        let targetDay = Math.min(baseDay, lastDayOfNextMonth);
        
        fechaActual = new Date(currentYear, nextMonth, targetDay);
      } else {
        const dias = parseInt(document.getElementById('credito_dias').value) || 30;
        fechaActual.setDate(fechaActual.getDate() + dias);
      }
    }

    //AGREGAR TOTALES AL FINAL DE LA TABLA
    const totalConIntereses = totalFinanciado + totalIntereses;
    const diferenciaInteres = totalConIntereses - montoFinanciar;

    tablaCuotas += `
    <tr class="table-light border-top border-2">
      <td colspan="2" class="text-end fw-bold">TOTALES:</td>
      <td class="text-end fw-bold">S/ ${totalFinanciado.toFixed(2)}</td>
      <td class="text-end fw-bold ${tasaInteres > 0 ? 'text-danger' : ''}">S/ ${totalIntereses.toFixed(2)}</td>
      <td class="text-end fw-bold text-success">S/ ${totalConIntereses.toFixed(2)}</td>
    </tr>
  `;

    //MOSTRAR EN LA TABLA
    document.getElementById('tablaCuotas').innerHTML = tablaCuotas;

    //AGREGAR DATOS GENERALES
    const adelantoExistente = document.getElementById("formCompra").querySelector('[name="monto_adelanto_general"]');
    if (adelantoExistente) {
      adelantoExistente.remove();
    }
    document.getElementById("formCompra").insertAdjacentHTML("beforeend", `
    <input type="hidden" class="cuota-hidden" name="monto_adelanto_general" value="${montoAdelanto.toFixed(2)}">
  `);

    const cuotasInput = document.getElementById("formCompra").querySelector('[name="credito_cuotas"]');
    if (!cuotasInput) {
      document.getElementById("formCompra").insertAdjacentHTML("beforeend", `
      <input type="hidden" class="cuota-hidden" name="credito_cuotas" value="${cantidadCuotas}">
    `);
    }

    //MOSTRAR RESUMEN VISUAL
    mostrarResumenCuotasCompra(totalCompra, montoAdelanto, montoFinanciar, totalConIntereses, diferenciaInteres, cantidadCuotas);
  }

  // NUEVA: Función para renderizar visualmente las cuotas que ya vienen de la base de datos
  function renderizarCuotasEditadas(cuotas, totalCompra) {
    let tablaCuotas = '';
    let totalFinanciado = 0;
    let totalIntereses = 0;
    const montoAdelantoTotal = cuotas.reduce((acc, c) => acc + (parseFloat(c.monto_adelanto) || 0), 0);
    const montoFinanciar = totalCompra - montoAdelantoTotal;

    cuotas.forEach(function (c, index) {
      const i = index + 1;
      const montoCuotaBase = parseFloat(c.monto);
      const interesCuota = parseFloat(c.interes);
      const totalCuota = parseFloat(c.total);
      
      totalFinanciado += montoCuotaBase;
      totalIntereses += interesCuota;
      
      tablaCuotas += `
      <tr>
        <td class="text-center"><strong>Cuota ${i}</strong></td>
        <td class="text-center">
          <input type="date" 
                 id="fecha_cuota_visual_${i}"
                 class="form-control form-control-sm fecha-cuota-editable" 
                 value="${c.fecha_vencimiento}" 
                 data-cuota="${i}"
                 onchange="actualizarFechaCuota(${i})">
        </td>
        <td class="text-end">S/ ${montoCuotaBase.toFixed(2)}</td>
        <td class="text-end ${interesCuota > 0 ? 'text-danger' : ''}">S/ ${interesCuota.toFixed(2)}</td>
        <td class="text-end fw-bold text-success">S/ ${totalCuota.toFixed(2)}</td>
      </tr>
      `;
    });

    const totalConIntereses = totalFinanciado + totalIntereses;
    tablaCuotas += `
    <tr class="table-light border-top border-2">
      <td colspan="2" class="text-end fw-bold">TOTALES:</td>
      <td class="text-end fw-bold">S/ ${totalFinanciado.toFixed(2)}</td>
      <td class="text-end fw-bold ${totalIntereses > 0 ? 'text-danger' : ''}">S/ ${totalIntereses.toFixed(2)}</td>
      <td class="text-end fw-bold text-success">S/ ${totalConIntereses.toFixed(2)}</td>
    </tr>
    `;
    
    document.getElementById('tablaCuotas').innerHTML = tablaCuotas;
    mostrarResumenCuotasCompra(totalCompra, montoAdelantoTotal, montoFinanciar, totalConIntereses, totalIntereses, cuotas.length);
    
    // Sincronizar el total configurado con el total de la compra actual
    totalConfiguracionCuotas = totalCompra;
  }

  //NUEVA FUNCIÓN: Actualizar fecha cuando el usuario la cambia
  function actualizarFechaCuota(numeroCuota) {
    const fechaVisual = document.getElementById(`fecha_cuota_visual_${numeroCuota}`).value;
    const fechaOculta = document.getElementById(`fecha_vencimiento_${numeroCuota}`);

    if (fechaOculta) {
      fechaOculta.value = fechaVisual;

      Swal.fire({
        icon: 'success',
        title: 'Fecha actualizada',
        text: `Cuota ${numeroCuota} reprogramada para ${fechaVisual}`,
        toast: true,
        position: 'top-end',
        showConfirmButton: false,
        timer: 2000,
        timerProgressBar: true
      });
    }
  }

  //FUNCIÓN MOSTRAR RESUMEN DE CUOTAS
  function mostrarResumenCuotasCompra(totalCompra, adelanto, montoFinanciar, totalConIntereses, intereses, numCuotas) {
    //CREAR O ACTUALIZAR RESUMEN
    let resumen = document.getElementById('resumenCuotasCompra');

    if (!resumen) {
      // Crear resumen si no existe
      const tabla = document.getElementById('tablaCuotas').parentElement;
      tabla.insertAdjacentHTML('beforebegin', `
      <div id="resumenCuotasCompra" class="alert alert-info mb-3">
        <div class="row">
          <div class="col-md-3">
            <strong><i class="fa-solid fa-shopping-cart me-2"></i>Total Compra:</strong><br>
            <span class="fs-5 text-primary" id="resumen_total_compra">S/ 0.00</span>
          </div>
          <div class="col-md-3">
            <strong><i class="fa-solid fa-hand-holding-dollar me-2"></i>Adelanto:</strong><br>
            <span class="fs-5 text-success" id="resumen_adelanto_compra">S/ 0.00</span>
          </div>
          <div class="col-md-3">
            <strong><i class="fa-solid fa-calendar-days me-2"></i>A Financiar (${numCuotas} cuotas):</strong><br>
            <span class="fs-5 text-warning" id="resumen_financiar_compra">S/ 0.00</span>
          </div>
          <div class="col-md-3">
            <strong><i class="fa-solid fa-percent me-2"></i>Total + Intereses:</strong><br>
            <span class="fs-5 text-danger" id="resumen_con_intereses_compra">S/ 0.00</span>
            <br><small class="text-muted" id="resumen_diferencia_compra">(+S/ 0.00 en intereses)</small>
          </div>
        </div>
      </div>
    `);
      resumen = document.getElementById('resumenCuotasCompra');
    }

    //ACTUALIZAR VALORES
    document.getElementById('resumen_total_compra').textContent = `S/ ${totalCompra.toFixed(2)}`;
    document.getElementById('resumen_adelanto_compra').textContent = `S/ ${adelanto.toFixed(2)}`;
    document.getElementById('resumen_financiar_compra').textContent = `S/ ${montoFinanciar.toFixed(2)}`;
    document.getElementById('resumen_con_intereses_compra').textContent = `S/ ${totalConIntereses.toFixed(2)}`;
    document.getElementById('resumen_diferencia_compra').textContent = `(+S/ ${intereses.toFixed(2)} en intereses)`;

    //ACTUALIZAR NÚMERO DE CUOTAS EN EL TEXTO
    resumen.querySelector('strong:nth-of-type(3)').innerHTML = `<i class="fa-solid fa-calendar-days me-2"></i>A Financiar (${numCuotas} cuotas):`;
  }


  //FUNCIÓN FORMATEAR FECHA
  function formatearFecha(fecha) {
    const dia = String(fecha.getDate()).padStart(2, '0');
    const mes = String(fecha.getMonth() + 1).padStart(2, '0');
    const anio = fecha.getFullYear();
    return `${dia}/${mes}/${anio}`;
  }

  function guardarYCerrarCuotas() {
    const tbody = document.getElementById("tablaCuotas");
    if (tbody.children.length === 0) {
      Swal.fire("Atención", "Debes generar las cuotas primero", "warning");
      return;
    }

    document.getElementById("tiene_cuotas").value = "1";

    Swal.fire({
      icon: "success",
      title: "Cuotas configuradas",
      text: "Las cuotas han sido guardadas correctamente",
      timer: 1500,
      showConfirmButton: false
    });

    // Sincronizar el total configurado al guardar
    totalConfiguracionCuotas = total;
    
    cerrarModalCuotas();
  }

  function cerrarModalCuotas() {
    const modalCuotas = bootstrap.Modal.getInstance(document.getElementById('modalCuotas'));
    if (modalCuotas) {
      modalCuotas.hide();
    }
    
    // RESTAURACIÓN: Re-mostrar el modal principal para que no se pierda el flujo
    const modalElem = document.getElementById('modalAgregarCompra');
    let modalCompra = bootstrap.Modal.getInstance(modalElem);
    if (!modalCompra || !modalElem.classList.contains('show')) {
        if (!modalCompra) modalCompra = new bootstrap.Modal(modalElem);
        modalCompra.show();
    }
  }

  //FUNCIÓN PARA EDITAR COMPRA
  function editarCompra(idCompra) {
    // Cerrar modal de detalle si está abierto
    const modalDetalle = bootstrap.Modal.getInstance(document.getElementById('detalleModal' + idCompra));
    if (modalDetalle) {
      modalDetalle.hide();
    }

    Swal.fire({
      title: 'Cargando datos...',
      html: 'Por favor espere',
      allowOutsideClick: false,
      allowEscapeKey: false,
      showConfirmButton: false,
      willOpen: () => {
        Swal.showLoading();
      }
    });

    $.ajax({
      url: `/api/obtener-compra/${idCompra}/`,
      method: 'GET',
      success: function (data) {
        if (data.success) {
          Swal.close();

          //LIMPIAR FORMULARIO
          $('#formCompra')[0].reset();
          $('#formVehiculo').hide();
          $('#formRepuesto').hide();
          $('#tablaDetalles').html('');
          itemIndex = 0;
          total = 0;
          $('#totalGeneral').text('0.00');
          $('#items_count').val('0');

          //CARGAR DATOS GENERALES
          $('#proveedor_search').val(data.compra.proveedor_nombre);
          $('#proveedor_id').val(data.compra.idproveedor);
          $('select[name="tipo_cliente"]').val(data.compra.idtipocliente);
          $('input[name="numcorrelativo"]').val(data.compra.numcorrelativo);
          $('input[name="fechacompra"]').val(data.compra.fechacompra);
          
          const formaPagoSelect = document.getElementById('forma_pago');
          formaPagoSelect.value = data.compra.id_forma_pago;
          
          // Deshabilitar forma de pago al editar
          $(formaPagoSelect).prop('disabled', true);
          // Asegurar que se envíe el valor al servidor
          if (!$('#forma_pago_hidden').length) {
            $('#formCompra').append('<input type="hidden" name="forma_pago" id="forma_pago_hidden">');
          }
          $('#forma_pago_hidden').val(data.compra.id_forma_pago);
          
          formaPagoSelect.dispatchEvent(new Event('change'));

          if (data.compra.id_tipo_pago) {
            $('#tipo_pago').val(data.compra.id_tipo_pago);
          }

          //CARGAR DETALLES
          data.detalles.forEach(function (d) {
            itemIndex++;
            $('#items_count').val(itemIndex);

            let nombre = '';
            let tipo = d.tipo;
            let extraInputs = '';
            const pCompra = parseFloat(d.precio_compra) || 0;
            const pMinimo = parseFloat(d.precio_minimo) || 0;
            const pMaximo = parseFloat(d.precio_maximo) || 0;
            const mMinimo = parseFloat(d.margen_minimo) || 0;
            const mMaximo = parseFloat(d.margen_maximo) || 0;
            const subtotal = d.cantidad * pCompra;
            total += subtotal;

            if (tipo === 'vehiculo') {
              nombre = d.nombre;
              extraInputs = `
              <input type="hidden" name="idproducto_${itemIndex}" value="${d.id_producto}">
              <input type="hidden" name="serie_motor_${itemIndex}" value="${d.serie_motor || ''}">
              <input type="hidden" name="serie_chasis_${itemIndex}" value="${d.serie_chasis || ''}">
              <input type="hidden" name="anio_${itemIndex}" value="${d.anio || ''}">
              <input type="hidden" name="idestadoproducto_${itemIndex}" value="${d.estado_producto}">
              <input type="hidden" name="imperfecciones_${itemIndex}" value="${d.imperfecciones || ''}">
              <input type="hidden" name="placas_${itemIndex}" value="${d.placas || ''}">
            `;
            } else if (tipo === 'repuesto') {
              nombre = d.nombre;
              extraInputs = `
              <input type="hidden" name="id_repuesto_${itemIndex}" value="${d.id_repuesto}">
              <input type="hidden" name="descripcion_${itemIndex}" value="${d.descripcion || ''}">
              <input type="hidden" name="modelo_${itemIndex}" value="${d.modelo || ''}">
            `;
            }

            const fila = `
            <tr id="fila_${itemIndex}">
              <td>${tipo}</td>
              <td>${nombre}</td>
              <td style="width: 100px;">
                <input type="number" name="cantidad_${itemIndex}" id="fila_cantidad_${itemIndex}" class="form-control form-control-sm text-end" value="${d.cantidad}" min="1" onchange="recalcularFilaCompra(${itemIndex})">
              </td>
              <td style="width: 130px;">
                <input type="number" name="precio_compra_${itemIndex}" id="fila_precio_compra_${itemIndex}" class="form-control form-control-sm text-end" value="${pCompra.toFixed(2)}" step="0.01" min="0" onchange="recalcularFilaCompra(${itemIndex})">
              </td>
              <td style="width: 130px;">
                <input type="number" name="precio_minimo_${itemIndex}" id="fila_precio_minimo_${itemIndex}" class="form-control form-control-sm text-end" value="${pMinimo.toFixed(2)}" step="0.01" min="0">
              </td>
              <td style="width: 130px;">
                <input type="number" name="precio_maximo_${itemIndex}" id="fila_precio_maximo_${itemIndex}" class="form-control form-control-sm text-end" value="${pMaximo.toFixed(2)}" step="0.01" min="0">
              </td>
              <td id="fila_subtotal_${itemIndex}" class="text-end fw-bold">${subtotal.toFixed(2)}</td>
              <td>
                <button type="button" class="btn btn-danger btn-sm" onclick="eliminarDetalle(${itemIndex})"><i class="fa-solid fa-trash"></i></button>
              </td>
              <td style="display:none">
                <input type="hidden" name="idcompradetalle_${itemIndex}" value="${d.idcompradetalle || ''}">
                <input type="hidden" name="tipo_item_${itemIndex}" value="${tipo}">
                <input type="hidden" name="margen_minimo_${itemIndex}" value="${mMinimo.toFixed(2)}">
                <input type="hidden" name="margen_maximo_${itemIndex}" value="${mMaximo.toFixed(2)}">
                ${extraInputs}
              </td>
            </tr>
          `;

            $('#tablaDetalles').append(fila);
          });

          $('#totalGeneral').text(total.toFixed(2));

          //CARGAR CUOTAS SI EXISTEN
          if (data.cuotas && data.cuotas.length > 0) {
            $('#tiene_cuotas').val('1');

            // Cargar datos de cuotas en el modal de cuotas
            $('#credito_cuotas').val(data.cuotas.length);
            $('#credito_tasa').val(data.cuotas[0].tasa);

            // Limpiar campos ocultos de cuotas anteriores
            $('.cuota-hidden').remove();

            // Agregar campos ocultos para cada cuota
            data.cuotas.forEach(function (cuota, index) {
              const i = index + 1;
              $('#formCompra').append(`
              <input type="hidden" class="cuota-hidden" name="numero_cuota_${i}" value="${cuota.numero_cuota}">
              <input type="hidden" class="cuota-hidden" name="monto_${i}" value="${parseFloat(cuota.monto).toFixed(2)}">
              <input type="hidden" class="cuota-hidden" name="tasa_${i}" value="${parseFloat(cuota.tasa).toFixed(2)}">
              <input type="hidden" class="cuota-hidden" name="interes_${i}" value="${parseFloat(cuota.interes).toFixed(2)}">
              <input type="hidden" class="cuota-hidden" name="total_${i}" value="${parseFloat(cuota.total).toFixed(2)}">
              <input type="hidden" class="cuota-hidden" id="fecha_vencimiento_${i}" name="fecha_vencimiento_${i}" value="${cuota.fecha_vencimiento}">
              <input type="hidden" class="cuota-hidden" name="monto_adelanto_${i}" value="${parseFloat(cuota.monto_adelanto).toFixed(2)}">
            `);
            });

            // CORRECCIÓN: Agregar también los campos de cabecera de crédito al formulario
            if (!$('#formCompra input[name="credito_cuotas"]').length) {
              $('#formCompra').append(`<input type="hidden" class="cuota-hidden" name="credito_cuotas" value="${data.cuotas.length}">`);
            } else {
              $('#formCompra input[name="credito_cuotas"]').val(data.cuotas.length);
            }

            const montoAdelantoTotal = data.cuotas.reduce((acc, c) => acc + (parseFloat(c.monto_adelanto) || 0), 0);
            if (!$('#formCompra input[name="monto_adelanto_general"]').length) {
              $('#formCompra').append(`<input type="hidden" class="cuota-hidden" name="monto_adelanto_general" value="${montoAdelantoTotal.toFixed(2)}">`);
            } else {
              $('#formCompra input[name="monto_adelanto_general"]').val(montoAdelantoTotal.toFixed(2));
            }
          }

          //CAMBIAR ACCIÓN DEL FORMULARIO Y TÍTULO
          $('#formCompra').attr('action', `/compras/actualizar/${idCompra}/`);
          $('#modalAgregarCompra .modal-title').text('Editar Compra');
          $('#guardarCompra').text('Actualizar Compra');

          // IMPORTANTE: Si hay cuotas, renderizarlas en el modal visual
          if (data.cuotas && data.cuotas.length > 0) {
              try {
                  renderizarCuotasEditadas(data.cuotas, total);
              } catch (e) {
                  console.error("Error al renderizar cuotas:", e);
              }
          }

          // Sincronizar el total inicial al cargar para edición (línea de base de confianza)
          totalConfiguracionCuotas = total;

          // Abrir modal - Usar instancia de Bootstrap si ya existe o crear una nueva
          const modalElem = document.getElementById('modalAgregarCompra');
          let modalCompra = bootstrap.Modal.getInstance(modalElem);
          if (!modalCompra) {
              modalCompra = new bootstrap.Modal(modalElem);
          }
          modalCompra.show();
        } else {
          Swal.close();
          Swal.fire({
            icon: 'warning',
            title: 'No se puede editar',
            text: data.error || 'Esta compra no puede ser editada.',
            confirmButtonText: 'OK'
          });
        }
      },
      error: function (xhr) {
        const codigo = xhr.responseJSON?.codigo;
        const errorMsg = xhr.responseJSON?.error || 'No se pudo cargar la compra';

        if (codigo === 'COMPRA_CREDITO_NO_EDITABLE') {
          Swal.fire({
            icon: 'warning',
            title: 'No se puede editar',
            text: errorMsg,
            confirmButtonText: 'OK'
          });
          return;
        }

        Swal.fire({
          title: 'Error',
          text: errorMsg,
          icon: 'error',
          confirmButtonText: 'OK'
        });
      }
    });
  }

  //FUNCIÓN PARA ELIMINAR COMPRA (CON VALIDACIÓN DE PERMISOS)
  function eliminarCompra(idCompra, numCorrelativo) {
    //VERIFICAR PERMISOS (solo admin o autorizado por WhatsApp)
    const esAdmin = 1;

    const button = document.querySelector(`[onclick*="eliminarCompra(${idCompra},"]`);
    const isAuthorized = button && button.getAttribute('data-authorized-bypass') === 'true';
    if (button) button.removeAttribute('data-authorized-bypass');

  if (!esAdmin && !isAuthorized) {
    Swal.fire({
      title: 'Sin permisos',
      html: `
        <p>Solo los administradores pueden eliminar compras.</p>
        <div class="alert alert-warning mt-3">
          <i class="fa-solid fa-shield-halved me-2"></i>
          Contacte con un administrador si necesita eliminar esta compra.
        </div>
      `,
      icon: 'warning',
      confirmButtonText: 'Entendido',
      confirmButtonColor: '#ffc107'
    });
    return;
  }

  Swal.fire({
    title: '¿Eliminar compra?',
    html: `
      <p>¿Está seguro de eliminar la compra <strong>#${numCorrelativo}</strong>?</p>
      <div class="alert alert-danger mt-3">
        <i class="fa-solid fa-triangle-exclamation me-2"></i>
        <strong>Advertencia:</strong> Esta acción cambiará el estado de la compra y quedará registrada en auditoría.
      </div>
      <div class="form-group mt-3 text-start">
        <label class="form-label fw-bold">Motivo de eliminación: <span class="text-danger">*</span></label>
        <textarea id="motivoEliminacion" class="form-control" rows="3" placeholder="Escriba el motivo (obligatorio)"></textarea>
      </div>
    `,
    icon: 'warning',
    showCancelButton: true,
    confirmButtonColor: '#dc3545',
    cancelButtonColor: '#6c757d',
    confirmButtonText: '<i class="fa-solid fa-trash me-2"></i>Sí, eliminar',
    cancelButtonText: '<i class="fa-solid fa-xmark me-2"></i>Cancelar',
    preConfirm: () => {
      const motivo = document.getElementById('motivoEliminacion').value.trim();
      if (!motivo) {
        Swal.showValidationMessage('Debe ingresar un motivo');
        return false;
      }
      return { motivo: motivo };
    }
  }).then((result) => {
    if (result.isConfirmed) {
      // Mostrar loading
      Swal.fire({
        title: 'Eliminando compra...',
        html: 'Por favor espere',
        allowOutsideClick: false,
        allowEscapeKey: false,
        showConfirmButton: false,
        willOpen: () => {
          Swal.showLoading();
        }
      });

      // Enviar petición AJAX para eliminar
      $.ajax({
        url: `/compras/eliminar/${idCompra}/`,
        method: 'POST',
        data: {
          'csrfmiddlewaretoken': '1',
          'motivo': result.value.motivo
        },
        success: function (response) {
          Swal.fire({
            title: '¡Eliminada!',
            html: `
              <p>La compra ha sido eliminada correctamente</p>
              <small class="text-muted">La acción ha sido registrada en auditoría</small>
            `,
            icon: 'success',
            timer: 2000,
            showConfirmButton: false
          }).then(() => {
            // Recargar la página
            window.location.reload();
          });
        },
        error: function (xhr) {
          let errorMsg = 'No se pudo eliminar la compra';

          if (xhr.responseJSON) {
            errorMsg = xhr.responseJSON.error || errorMsg;

            //MANEJAR ERROR DE PERMISOS
            if (xhr.responseJSON.codigo === 'SIN_PERMISOS') {
              Swal.fire({
                title: 'Sin permisos',
                text: errorMsg,
                icon: 'warning',
                confirmButtonText: 'Entendido',
                confirmButtonColor: '#ffc107'
              });
              return;
            }
          }

          Swal.fire({
            title: 'Error',
            text: errorMsg,
            icon: 'error',
            confirmButtonText: 'OK'
          });
        }
      });
    }
  });
}



// =====================================================================
// GENERACIÓN AUTOMÁTICA DE NOMBRE (REPLICADO DE VEHÍCULOS)
// =====================================================================
function actualizarNombreGenerico(isRepuesto = false) {
  var parts = [];
  var elements = [];
  var inputId = '';

  if (isRepuesto) {
    inputId = 'nr_nombre';
    elements = ['#nr_base_nombre', '#nr_idmarca', '#nr_idcolor'];
  } else {
    inputId = 'np_nomproducto';
    elements = ['#np_idcategoria', '#np_marca_search_add', '#np_modelo_search_add', '#np_id_configuracion', '#np_color_search_add', '#np_detalle_color_search_add'];
  }

  elements.forEach(function (selector) {
    var $el = $(selector);
    var txt = '';
    if ($el.is('select')) {
      txt = $el.find('option:selected').text().trim();
    } else if ($el.is('input')) {
      txt = $el.val().trim();
    }

    if (txt && txt.indexOf('--') === -1 && txt.indexOf('Seleccione') === -1 && txt.indexOf('Ningun') === -1) {
      parts.push(txt);
    }
  });

  $('#' + inputId).val(parts.join(' '));
}

// Eventos para Vehículos
$(document).on('change', '.select-auto-veh', function () {
  actualizarNombreGenerico(false);
});



// =====================================================================
// REGISTRO RÁPIDO: VEHÍCULO EN CATÁLOGO
// =====================================================================
function abrirModalNuevoProducto() {
  // Ocultar el modal de compra temporalmente para evitar conflictos de z-index
  const modalCompraEl = document.getElementById('modalAgregarCompra');
  const modalCompra = bootstrap.Modal.getInstance(modalCompraEl);
  if (modalCompra) modalCompra.hide();

  // Limpiar el formulario
  document.getElementById('formNuevoProductoCompra').reset();
  document.getElementById('alertNuevoProducto').innerHTML = '';

  // Esperar a que cierre el modal de compra antes de abrir el de producto
  setTimeout(() => {
    const modalProd = new bootstrap.Modal(document.getElementById('modalNuevoProductoCompra'));
    modalProd.show();
  }, 350);
}

function cerrarModalNuevoProducto() {
  const modalProdEl = document.getElementById('modalNuevoProductoCompra');
  const modalProd = bootstrap.Modal.getInstance(modalProdEl);
  if (modalProd) modalProd.hide();

  // Reabrir el modal de compra
  setTimeout(() => {
    const modalCompra = new bootstrap.Modal(document.getElementById('modalAgregarCompra'));
    modalCompra.show();
  }, 350);
}

async function guardarNuevoProducto() {
  const alertBox = document.getElementById('alertNuevoProducto');
  alertBox.innerHTML = '';

  const form = document.getElementById('formNuevoProductoCompra');
  const formData = new FormData(form);
  const csrfToken = form.querySelector('[name=csrfmiddlewaretoken]').value;

  // Validación básica en el cliente
  const nombre = document.getElementById('np_nomproducto').value.trim();
  const marca   = document.getElementById('np_idmarca').value;
  const cat     = document.getElementById('np_idcategoria').value;
  const cil     = document.getElementById('np_idcilindrada').value;
  const col     = document.getElementById('np_idcolor').value;
  const uni     = document.getElementById('np_idunidad').value;

  if (!nombre || !marca || !cat || !cil || !col || !uni) {
    alertBox.innerHTML = '<div class="alert alert-danger py-2"><i class="fa-solid fa-triangle-exclamation me-2"></i>Complete todos los campos obligatorios (*)</div>';
    return;
  }

  const btn = document.getElementById('btnGuardarNuevoProducto');
  btn.disabled = true;
  btn.innerHTML = '<span class="spinner-border spinner-border-sm me-2"></span>Guardando...';

  try {
    const resp = await fetch('/api/compras/crear-producto/', {
      method: 'POST',
      headers: { 'X-CSRFToken': csrfToken },
      body: formData,
    });
    const data = await resp.json();

    if (data.ok) {
      // Inyectar el nuevo producto en vehiculosData y seleccionarlo
      vehiculosData.push({ id: data.id, text: data.nombre });

      document.getElementById('vehiculo_search').value = data.nombre;
      document.getElementById('veh_nombre').value = data.id;

      // Mostrar éxito breve y cerrar
      alertBox.innerHTML = `<div class="alert alert-success py-2"><i class="fa-solid fa-circle-check me-2"></i>${data.mensaje}</div>`;
      setTimeout(() => {
        cerrarModalNuevoProducto();
      }, 1200);

    } else {
      alertBox.innerHTML = `<div class="alert alert-danger py-2"><i class="fa-solid fa-triangle-exclamation me-2"></i>${data.error}</div>`;
    }
  } catch (err) {
    alertBox.innerHTML = '<div class="alert alert-danger py-2">Error de conexión. Intente nuevamente.</div>';
  } finally {
    btn.disabled = false;
    btn.innerHTML = '<i class="fa-solid fa-save me-2"></i>Guardar Vehículo';
  }
}

// =====================================================================
// REGISTRO RÁPIDO: REPUESTO EN CATÁLOGO
// =====================================================================
function abrirModalNuevoRepuesto() {
  // Ocultar el modal de compra temporalmente
  const modalCompraEl = document.getElementById('modalAgregarCompra');
  const modalCompra = bootstrap.Modal.getInstance(modalCompraEl);
  if (modalCompra) modalCompra.hide();

  // Limpiar el formulario
  document.getElementById('formNuevoRepuestoCompra').reset();
  document.getElementById('alertNuevoRepuesto').innerHTML = '';

  setTimeout(() => {
    const modalRep = new bootstrap.Modal(document.getElementById('modalNuevoRepuestoCompra'));
    modalRep.show();
  }, 350);
}

function cerrarModalNuevoRepuesto() {
  const modalRepEl = document.getElementById('modalNuevoRepuestoCompra');
  const modalRep = bootstrap.Modal.getInstance(modalRepEl);
  if (modalRep) modalRep.hide();

  // Reabrir el modal de compra
  setTimeout(() => {
    const modalCompra = new bootstrap.Modal(document.getElementById('modalAgregarCompra'));
    modalCompra.show();
  }, 350);
}

async function guardarNuevoRepuesto() {
  const alertBox = document.getElementById('alertNuevoRepuesto');
  alertBox.innerHTML = '';

  const form = document.getElementById('formNuevoRepuestoCompra');
  const formData = new FormData(form);
  const csrfToken = form.querySelector('[name=csrfmiddlewaretoken]').value;

  // Validación básica en el cliente
  const nombre = document.getElementById('nr_nombre').value.trim();
  const marca  = document.getElementById('nr_marca_rep_id_add').value;
  const uni    = document.getElementById('nr_unidad_rep_id_add').value;

  if (!nombre || !marca || !uni) {
    alertBox.innerHTML = '<div class="alert alert-danger py-2"><i class="fa-solid fa-triangle-exclamation me-2"></i>Complete todos los campos obligatorios (*) (Nombre, Marca, Unidad)</div>';
    return;
  }

  const btn = document.getElementById('btnGuardarNuevoRepuesto');
  btn.disabled = true;
  btn.innerHTML = '<span class="spinner-border spinner-border-sm me-2"></span>Guardando...';

  try {
    const resp = await fetch('/api/compras/crear-repuesto/', {
      method: 'POST',
      headers: { 'X-CSRFToken': csrfToken },
      body: formData,
    });
    const data = await resp.json();

    if (data.ok) {
      // Inyectar el nuevo repuesto en repuestosData y seleccionarlo
      repuestosData.push({ id: data.id, text: data.nombre });

      document.getElementById('repuesto_search').value = data.nombre;
      document.getElementById('rep_nombre').value = data.id;

      // Mostrar éxito breve y cerrar
      alertBox.innerHTML = `<div class="alert alert-success py-2"><i class="fa-solid fa-circle-check me-2"></i>${data.mensaje}</div>`;
      setTimeout(() => {
        cerrarModalNuevoRepuesto();
      }, 1200);

    } else {
      alertBox.innerHTML = `<div class="alert alert-danger py-2"><i class="fa-solid fa-triangle-exclamation me-2"></i>${data.error}</div>`;
    }
  } catch (err) {
    alertBox.innerHTML = '<div class="alert alert-danger py-2">Error de conexión. Intente nuevamente.</div>';
  } finally {
    btn.disabled = false;
    btn.innerHTML = '<i class="fa-solid fa-save me-2"></i>Guardar Repuesto';
  }
}
// ---- GESTIÓN MÚLTIPLES MÉTODOS DE PAGO — COMPRA ----
let pagoCompraCount = 0;
const TIPOS_PAGO_COMPRA_TPL = `<option value="1">1</option>`;

function agregarFilaPagoCompra(tpId='', monto='', operacion='') {
    pagoCompraCount++;
    const div = document.createElement('div');
    div.className = 'pago-row-compra row g-2 mb-2 align-items-center';
    div.id = `pago-row-compra-${pagoCompraCount}`;
    div.innerHTML = `
      <div class="col-md-5 col-selector-c">
        <select name="tipo_pago_id[]" class="form-select form-select-sm select-tipo-pago-compra"
                required onchange="toggleOperacionCompra(this)">
          <option value="">Método de Pago...</option>
          ${TIPOS_PAGO_COMPRA_TPL}
        </select>
      </div>
      <div class="col-md-4 nro-op-compra-container d-none">
        <input type="text" name="nro_operacion[]" class="form-control form-control-sm nro-operacion-input"
               placeholder="N° Operación" value="${operacion}">
      </div>
      <div class="col-md-3 flex-grow-1 col-monto-c">
        <div class="input-group input-group-sm">
          <span class="input-group-text bg-white">S/</span>
          <input type="number" name="monto_pago[]" class="form-control form-control-sm monto-pago-compra"
                 step="0.01" min="0.01" placeholder="0.00" value="${monto}" required
                 oninput="calcularTotalPagadoCompra()">
          <button type="button" class="btn btn-sm btn-outline-danger btn-remove-pago-compra"
                  title="Eliminar" onclick="eliminarFilaPagoCompra(this)">
            <i class="fa-solid fa-minus"></i>
          </button>
        </div>
      </div>`;
    document.getElementById('pagos-container-compra').appendChild(div);
    const sel = div.querySelector('select');
    if (tpId) { sel.value = tpId; }
    else if (pagoCompraCount === 1) {
        for (let opt of sel.options) {
            if (opt.textContent.trim().toLowerCase().includes('efectivo')) {
                sel.value = opt.value; break;
            }
        }
    }
    toggleOperacionCompra(sel);
    actualizarBotonesEliminarCompra();
    calcularTotalPagadoCompra();
}

function toggleOperacionCompra(select) {
    const row = select.closest('.pago-row-compra');
    const container = row.querySelector('.nro-op-compra-container');
    const input = container.querySelector('input');
    const texto = (select.options[select.selectedIndex]?.text || '').toLowerCase();
    const esEfectivo = texto.includes('efectivo') || select.value === '';
    
    // Si contiene 'múltiple', es un tipo genérico que no debe usarse directamente aquí
    // pero si lo eligen, requerir operación por si acaso.
    
    if (!esEfectivo && select.value !== '') {
        container.classList.remove('d-none');
        input.required = true;
        row.querySelector('.col-selector-c').className = 'col-md-4 col-selector-c';
        container.className = 'col-md-4 nro-op-compra-container';
        row.querySelector('.col-monto-c').className = 'col-md-4 flex-grow-1 col-monto-c';
    } else {
        container.classList.add('d-none');
        input.required = false;
        input.value = '';
        row.querySelector('.col-selector-c').className = 'col-md-5 col-selector-c';
        row.querySelector('.col-monto-c').className = 'col-md-3 flex-grow-1 col-monto-c';
    }
}

function eliminarFilaPagoCompra(btn) {
    btn.closest('.pago-row-compra').remove();
    calcularTotalPagadoCompra();
    actualizarBotonesEliminarCompra();
}

function actualizarBotonesEliminarCompra() {
    const btns = document.querySelectorAll('.btn-remove-pago-compra');
    btns.forEach(b => b.disabled = (btns.length === 1));
}

function calcularTotalPagadoCompra() {
    let totalP = 0;
    document.querySelectorAll('.monto-pago-compra').forEach(inp => {
        totalP += parseFloat(inp.value) || 0;
    });
    const lbl = document.getElementById('total_pagado_compra_lbl');
    if (lbl) lbl.textContent = `S/ ${totalP.toFixed(2)}`;
}

function resetearPagosCompra() {
    const container = document.getElementById('pagos-container-compra');
    if (container) {
        container.innerHTML = '';
        pagoCompraCount = 0;
        agregarFilaPagoCompra();
    }
}

document.addEventListener("DOMContentLoaded", function () {
    resetearPagosCompra();
});
  // ===================== VARIABLES PARA AUTOCOMPLETADO =====================
  const marcasData = [
    { id: "1", text: "1" },
  ];
  const modelosData = [
    { id: "1", text: "1" },
  ];
  const cilindradasData = [
    { id: "1", text: "1" },
  ];
  const coloresData = [
    { id: "1", text: "1" },
  ];
  const detallesColorData = [
    { id: "1", text: "1" },
  ];
  const unidadesData = [
    { id: "1", text: "1" },
  ];

  // ===================== FUNCIONES GENERICAS DE AUTOCOMPLETADO =====================
  function toggleAutocompleteNew(inputId, resultsId, data, hiddenId) {
    var $results = $('#' + resultsId);
    if ($results.is(':visible')) {
      $results.hide();
    } else {
      filterAutocompleteNew(inputId, resultsId, data, hiddenId);
      $results.show();
    }
  }

  function filterAutocompleteNew(inputId, resultsId, data, hiddenId) {
    var query = $('#' + inputId).val().toLowerCase();
    var $results = $('#' + resultsId);
    $results.empty();
    
    var filtered = query ? data.filter(item => item.text.toLowerCase().includes(query)) : data;
    
    if (filtered.length === 0) {
      $results.append('<div class="autocomplete-item text-muted">No se encontraron resultados</div>');
      return;
    }
    
    filtered.forEach(function(item) {
      var $div = $('<div class="autocomplete-item"></div>').text(item.text);
      $div.on('click', function() {
        $('#' + inputId).val(item.text);
        $('#' + hiddenId).val(item.id);
        $results.hide();
        if (typeof actualizarNombreGenerico === 'function') actualizarNombreGenerico(false);
      });
      $results.append($div);
    });
  }

  function setupAutocompleteNew(inputId, resultsId, data, hiddenId) {
    $('#' + inputId).on('input', function() {
      $('#' + hiddenId).val('');
      filterAutocompleteNew(inputId, resultsId, data, hiddenId);
      $('#' + resultsId).show();
      if (typeof actualizarNombreGenerico === 'function') actualizarNombreGenerico(false);
    });
    
    $(document).on('click', function(e) {
      if (!$(e.target).closest('.autocomplete-wrapper').length) {
        $('.autocomplete-results').hide();
      }
    });
  }

  setupAutocompleteNew('np_marca_search_add', 'np_marca_results_add', marcasData, 'np_idmarca');
  setupAutocompleteNew('np_modelo_search_add', 'np_modelo_results_add', modelosData, 'np_idmodelo');
  setupAutocompleteNew('np_cilindrada_search_add', 'np_cilindrada_results_add', cilindradasData, 'np_idcilindrada');
  setupAutocompleteNew('np_color_search_add', 'np_color_results_add', coloresData, 'np_idcolor');
  setupAutocompleteNew('np_detalle_color_search_add', 'np_detalle_color_results_add', detallesColorData, 'np_id_detalle_color');

  setupAutocompleteNew('nr_categoria_rep_search_add', 'nr_categoria_rep_results_add', categoriasRepData, 'nr_categoria_rep_id_add');
  setupAutocompleteNew('nr_marca_rep_search_add', 'nr_marca_rep_results_add', marcasRepData, 'nr_marca_rep_id_add');
  setupAutocompleteNew('nr_unidad_rep_search_add', 'nr_unidad_rep_results_add', unidadesData, 'nr_unidad_rep_id_add');
  setupAutocompleteNew('nr_garantia_rep_search_add', 'nr_garantia_rep_results_add', garantiasRepData, 'nr_garantia_rep_id_add');

  // ===================== REGISTRO RÁPIDO (MINI-MODALES) =====================
  var miniModalActive = false;
  var currentMainModalId = 'modalNuevoProductoCompra'; // Default
  function setMainModal(id) { currentMainModalId = id; }
  document.querySelectorAll('[data-bs-target^="#miniModal"]').forEach(function(btn) {
    btn.addEventListener('click', function() {
      miniModalActive = true;
    }, true);
  });

  function guardarRapidoAutoComplete(url, datos, inputBusquedaId, hiddenId, resultsId, dataArray, miniModalId, limpiarFn) {
    $.ajax({
      url: url,
      type: 'POST',
      data: Object.assign({ csrfmiddlewaretoken: '1' }, datos),
      success: function(res) {
        if (res.ok) {
          dataArray.push({ id: res.id, text: res.nombre });
          $('#' + inputBusquedaId).val(res.nombre);
          $('#' + hiddenId).val(res.id);
          var el = document.getElementById(miniModalId);
          if(el) { var m = bootstrap.Modal.getInstance(el); if(m) m.hide(); }
          if (limpiarFn) limpiarFn();
          Swal.fire({ icon: 'success', title: '¡Guardado!', text: '"' + res.nombre + '" fue creado y seleccionado.', timer: 1800, showConfirmButton: false });
        } else {
          Swal.fire({ icon: 'error', title: 'Error', text: res.error || 'No se pudo guardar.' });
        }
      },
      error: function() {
        Swal.fire({ icon: 'error', title: 'Error', text: 'Error en la petición.' });
      }
    });
  }

  function guardarRapidoSelect(url, datos, selectId, miniModalId, limpiarFn) {
    $.ajax({
      url: url,
      type: 'POST',
      data: Object.assign({ csrfmiddlewaretoken: '1' }, datos),
      success: function(res) {
        if (res.ok) {
          $('#' + selectId).append('<option value="' + res.id + '">' + res.nombre + '</option>').val(res.id);
          var el = document.getElementById(miniModalId);
          if(el) { var m = bootstrap.Modal.getInstance(el); if(m) m.hide(); }
          if (limpiarFn) limpiarFn();
          Swal.fire({ icon: 'success', title: '¡Guardado!', text: '"' + res.nombre + '" fue creado y seleccionado.', timer: 1800, showConfirmButton: false });
        } else {
          Swal.fire({ icon: 'error', title: 'Error', text: res.error || 'No se pudo guardar.' });
        }
      },
      error: function() {
        Swal.fire({ icon: 'error', title: 'Error', text: 'Error en la petición.' });
      }
    });
  }

  $('#btn_guardar_marca_rapida').on('click', function() {
    var nombre = $('#input_nueva_marca').val().trim();
    if (!nombre) { Swal.fire({ icon: 'warning', title: 'Atención', text: 'El nombre no puede estar vacío.' }); return; }
    var searchId = currentMainModalId === 'modalNuevoRepuestoCompra' ? 'nr_marca_search_add' : 'np_marca_search_add';
    var hiddenId = currentMainModalId === 'modalNuevoRepuestoCompra' ? 'nr_idmarca' : 'np_idmarca';
    var resultsId = currentMainModalId === 'modalNuevoRepuestoCompra' ? 'nr_marca_results_add' : 'np_marca_results_add';
    guardarRapidoAutoComplete("", { nameMarcaAgregar: nombre }, searchId, hiddenId, resultsId, marcasData, 'miniModalMarca', function() { $('#input_nueva_marca').val(''); });
  });

  $('#btn_guardar_modelo_rapido').on('click', function() {
    var nombre = $('#input_nuevo_modelo').val().trim();
    if (!nombre) { Swal.fire({ icon: 'warning', title: 'Atención', text: 'El nombre no puede estar vacío.' }); return; }
    var searchId = currentMainModalId === 'modalNuevoRepuestoCompra' ? 'nr_modelo_search_add' : 'np_modelo_search_add';
    var hiddenId = currentMainModalId === 'modalNuevoRepuestoCompra' ? 'nr_idmodelo' : 'np_idmodelo';
    var resultsId = currentMainModalId === 'modalNuevoRepuestoCompra' ? 'nr_modelo_results_add' : 'np_modelo_results_add';
    guardarRapidoAutoComplete("", { nameModeloAgregar: nombre }, searchId, hiddenId, resultsId, modelosData, 'miniModalModelo', function() { $('#input_nuevo_modelo').val(''); });
  });

  $('#btn_guardar_config_rapida').on('click', function() {
    var nombre = $('#input_nueva_config').val().trim();
    if (!nombre) { Swal.fire({ icon: 'warning', title: 'Atención', text: 'El nombre no puede estar vacío.' }); return; }
    guardarRapidoSelect("", { nombre: nombre }, 'np_id_configuracion', 'miniModalConfig', function() { $('#input_nueva_config').val(''); });
  });

  $('#btn_guardar_cilindrada_rapida').on('click', function() {
    var nombre = $('#input_nueva_cilindrada').val().trim();
    if (!nombre) { Swal.fire({ icon: 'warning', title: 'Atención', text: 'La cilindrada no puede estar vacía.' }); return; }
    guardarRapidoAutoComplete("", { nameCilindradaAgregar: nombre }, 'np_cilindrada_search_add', 'np_idcilindrada', 'np_cilindrada_results_add', cilindradasData, 'miniModalCilindrada', function() { $('#input_nueva_cilindrada').val(''); });
  });

  // Guardar rápido - Color
  $('#btn_guardar_color_rapido').on('click', function() {
    var nombre = $('#input_nuevo_color').val().trim();
    if (!nombre) {
      Swal.fire({ title: 'Atención', text: 'Ingrese el nombre del color.', icon: 'warning' });
      return;
    }
    var searchId = currentMainModalId === 'modalNuevoRepuestoCompra' ? 'nr_color_search_add' : 'np_color_search_add';
    var hiddenId = currentMainModalId === 'modalNuevoRepuestoCompra' ? 'nr_idcolor' : 'np_idcolor';
    var resultsId = currentMainModalId === 'modalNuevoRepuestoCompra' ? 'nr_color_results_add' : 'np_color_results_add';
    guardarRapidoAutoComplete("", { nameColorAgregar: nombre }, searchId, hiddenId, resultsId, coloresData, 'miniModalColor', function() { $('#input_nuevo_color').val(''); });
  });

  // Guardar rápido - Detalle de Color
  $('#btn_guardar_detalle_color_rapida').click(function () {
    var nombre = $('#input_nuevo_detalle_color').val().trim();
    if (!nombre) {
      Swal.fire({ title: 'Atención', text: 'Ingrese el nombre del detalle de color.', icon: 'warning' });
      return;
    }
    guardarRapidoAutoComplete("", { nombre: nombre }, 'np_detalle_color_search_add', 'np_id_detalle_color', 'np_detalle_color_results_add', detallesColorData, 'miniModalDetalleColor', function() { $('#input_nuevo_detalle_color').val(''); });
  });

  $('#btn_guardar_unidad_rapida').on('click', function() {
    var codigo = $('#input_nueva_unidad_codigo').val().trim();
    var nombre = $('#input_nueva_unidad_nombre').val().trim();
    if (!codigo || !nombre) { Swal.fire({ icon: 'warning', title: 'Atención', text: 'El código y la abreviación son obligatorios.' }); return; }
    if (currentMainModalId === 'modalNuevoRepuestoCompra') {
      guardarRapidoAutoComplete("", { codigo_sunat: codigo, abrunidad: nombre, nombre: nombre }, 'nr_unidad_search_add', 'nr_idunidad', 'nr_unidad_results_add', unidadesData, 'miniModalUnidad', function() { $('#input_nueva_unidad_codigo, #input_nueva_unidad_nombre').val(''); });
    } else {
      guardarRapidoSelect("", { codigo_sunat: codigo, abrunidad: nombre }, 'np_idunidad', 'miniModalUnidad', function() { $('#input_nueva_unidad_codigo, #input_nueva_unidad_nombre').val(''); });
    }
  });


  // --- CATEGORÍA REPUESTO ---
  $('#btn_guardar_categoria_rep_rapida').on('click', function() {
    var nombre = $('#input_nueva_categoria_rep').val().trim();
    if (!nombre) { Swal.fire({ icon: 'warning', title: 'Atención', text: 'El nombre de la categoría no puede estar vacío.' }); return; }
    guardarRapidoAutoComplete("", { nomcategoria: nombre }, 
      'nr_categoria_rep_search_add', 'nr_categoria_rep_id_add', 'nr_categoria_rep_results_add', 
      categoriasRepData, 'miniModalCategoriaRep', function() { $('#input_nueva_categoria_rep').val(''); });
  });

  // --- MARCA REPUESTO ---
  $('#btn_guardar_marca_rep_rapida').on('click', function() {
    var nombre = $('#input_nueva_marca_rep').val().trim();
    if (!nombre) { Swal.fire({ icon: 'warning', title: 'Atención', text: 'El nombre de la marca no puede estar vacío.' }); return; }
    guardarRapidoAutoComplete("", { nombremarca: nombre }, 
      'nr_marca_rep_search_add', 'nr_marca_rep_id_add', 'nr_marca_rep_results_add', 
      marcasRepData, 'miniModalMarcaRep', function() { $('#input_nueva_marca_rep').val(''); });
  });

  // --- UNIDAD REPUESTO ---
  $('#btn_guardar_unidad_rep_rapida').on('click', function() {
    var codigo = $('#input_nueva_unidad_codigo_rep').val().trim();
    var nombre = $('#input_nueva_unidad_nombre_rep').val().trim();
    if (!codigo || !nombre) { Swal.fire({ icon: 'warning', title: 'Atención', text: 'El código y la abreviación son obligatorios.' }); return; }
    guardarRapidoAutoComplete("", { codigo_sunat: codigo, abrunidad: nombre, nombre: nombre }, 
      'nr_unidad_rep_search_add', 'nr_unidad_rep_id_add', 'nr_unidad_rep_results_add', 
      unidadesData, 'miniModalUnidadRep', function() { $('#input_nueva_unidad_codigo_rep, #input_nueva_unidad_nombre_rep').val(''); });
  });

  // --- GARANTÍA REPUESTO ---
  $('#btn_guardar_garantia_rep_rapida').on('click', function() {
    var nombre = $('#input_nueva_garantia_rep').val().trim();
    if (!nombre) { Swal.fire({ icon: 'warning', title: 'Atención', text: 'El nombre de la garantía no puede estar vacío.' }); return; }
    guardarRapidoAutoComplete("", { nombre: nombre }, 
      'nr_garantia_rep_search_add', 'nr_garantia_rep_id_add', 'nr_garantia_rep_results_add', 
      garantiasRepData, 'miniModalGarantiaRep', function() { $('#input_nueva_garantia_rep').val(''); });
  });

  ['miniModalMarca','miniModalModelo','miniModalConfig','miniModalCilindrada','miniModalColor','miniModalDetalleColor','miniModalUnidad',
   'miniModalCategoriaRep','miniModalMarcaRep','miniModalUnidadRep','miniModalGarantiaRep'].forEach(function(id) {
    var el = document.getElementById(id);
    if(el) {
      el.addEventListener('hidden.bs.modal', function() {
        miniModalActive = false;
        if (currentMainModalId) {
          var mainModalEl = document.getElementById(currentMainModalId);
          if(mainModalEl) {
            var mainModal = bootstrap.Modal.getInstance(mainModalEl);
            if (!mainModal) new bootstrap.Modal(mainModalEl).show();
            else mainModal.show();
          }
        }
      });
    }
  });
