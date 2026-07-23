
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
