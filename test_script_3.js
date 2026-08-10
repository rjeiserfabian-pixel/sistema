
// ==========================================
// CONFIGURACIÓN DE PAGINACIÓN
// ==========================================

const CONFIG_PAG = {
  productos: 10,
  filas: 10
};

function renderPaginador(container, totalItems, itemsPerPage, currentPage, onPageChange) {
  const totalPages = Math.ceil(totalItems / itemsPerPage);
  container.empty();
  
  if (totalPages <= 1) return;

  let html = `<nav aria-label="Page navigation"><ul class="pagination pagination-sm mb-0">`;
  
  // Botón anterior
  html += `<li class="page-item ${currentPage === 1 ? 'disabled' : ''}">
             <a class="page-link" href="#" data-page="${currentPage - 1}">&laquo;</a>
           </li>`;

  for (let i = 1; i <= totalPages; i++) {
    html += `<li class="page-item ${i === currentPage ? 'active' : ''}">
               <a class="page-link" href="#" data-page="${i}">${i}</a>
             </li>`;
  }

  html += `<li class="page-item ${currentPage === totalPages ? 'disabled' : ''}">
             <a class="page-link" href="#" data-page="${currentPage + 1}">&raquo;</a>
           </li></ul></nav>`;

  container.html(html);
  
  container.find('.page-link').on('click', function(e) {
    e.preventDefault();
    const newPage = parseInt($(this).attr('data-page'));
    if (!isNaN(newPage) && newPage !== currentPage && newPage >= 1 && newPage <= totalPages) {
      onPageChange(newPage);
    }
  });
}

function aplicarPaginacionGlobal() {
  // Paginación de Vehículos (Productos)
  const vehiculosVisibles = $('.vehiculo-card:visible');
  const totalVehiculos = vehiculosVisibles.length;
  let currentVehiculoPage = 1;

  function showVehiculoPage(page) {
    currentVehiculoPage = page;
    vehiculosVisibles.hide();
    vehiculosVisibles.slice((page - 1) * CONFIG_PAG.productos, page * CONFIG_PAG.productos).show();
    renderPaginador($('#paginacionProductosVehiculos'), totalVehiculos, CONFIG_PAG.productos, currentVehiculoPage, showVehiculoPage);
    
    // Aplicar paginación de filas a los vehículos que se muestran
    vehiculosVisibles.slice((page - 1) * CONFIG_PAG.productos, page * CONFIG_PAG.productos).each(function() {
      aplicarPaginacionFilas($(this), '.vehiculo-row');
    });
  }

  // Paginación de Repuestos (Productos)
  const repuestosVisibles = $('.repuesto-card:visible');
  const totalRepuestos = repuestosVisibles.length;
  let currentRepuestoPage = 1;

  function showRepuestoPage(page) {
    currentRepuestoPage = page;
    repuestosVisibles.hide();
    repuestosVisibles.slice((page - 1) * CONFIG_PAG.productos, page * CONFIG_PAG.productos).show();
    renderPaginador($('#paginacionProductosRepuestos'), totalRepuestos, CONFIG_PAG.productos, currentRepuestoPage, showRepuestoPage);
    
    // Aplicar paginación de filas a los repuestos que se muestran
    repuestosVisibles.slice((page - 1) * CONFIG_PAG.productos, page * CONFIG_PAG.productos).each(function() {
      aplicarPaginacionFilas($(this), '.repuesto-row');
    });
  }

  function aplicarPaginacionFilas(card, rowSelector) {
    const rows = card.find(`tbody tr${rowSelector}:visible`);
    const totalRows = rows.length;
    let currentRowPage = 1;

    function showRowPage(page) {
      currentRowPage = page;
      rows.hide();
      rows.slice((page - 1) * CONFIG_PAG.filas, page * CONFIG_PAG.filas).show();
      renderPaginador(card.find('.paginacion-filas'), totalRows, CONFIG_PAG.filas, currentRowPage, showRowPage);
    }

    if (totalRows > 0) showRowPage(1);
    else card.find('.paginacion-filas').empty();
  }

  showVehiculoPage(1);
  showRepuestoPage(1);
}

$(document).ready(function() {
  // Inicializar paginación al cargar
  aplicarPaginacionGlobal();

  // Búsqueda de Vehículos
  $('#buscarVehiculo').on('input', function() {
    let query = $(this).val().toLowerCase().trim();
    let totalUnidades = 0;
    let totalProductos = 0;

    if (query.length > 0) {
      $('#seccionRepuestos').hide();
    } else if ($('#buscarRepuesto').val().length === 0) {
      $('#seccionRepuestos').show();
    }

    $('.vehiculo-card').each(function() {
      let card = $(this);
      let productName = card.attr('data-nombre');
      let rows = card.find('tbody tr.vehiculo-row');
      let cardVisible = false;
      let cardTotalUnidades = 0;

      rows.each(function() {
        let row = $(this);
        let motor = row.find('.serie-motor').text().toLowerCase();
        let chasis = row.find('.serie-chasis').text().toLowerCase();
        let anio = row.find('.anio').text().toLowerCase();
        
        let match = productName.includes(query) || motor.includes(query) || chasis.includes(query) || anio.includes(query);
        
        if (match) {
          row.show();
          cardVisible = true;
          let cantidadStr = row.find('.cantidad-badge').text().trim();
          cardTotalUnidades += parseInt(cantidadStr) || 0;
        } else {
          row.hide();
        }
      });

      if (cardVisible) {
        card.show();
        totalProductos++;
        totalUnidades += cardTotalUnidades;
      } else {
        card.hide();
      }
    });

    $('#totalProductosVehiculos').text(totalProductos);
    $('#totalUnidadesVehiculos').text(totalUnidades);
    
    // RE-APLICAR PAGINACIÓN TRAS BÚSQUEDA
    aplicarPaginacionGlobal();
  });

  // Búsqueda de Repuestos
  $('#buscarRepuesto').on('input', function() {
    let query = $(this).val().toLowerCase().trim();
    let totalUnidades = 0;
    let totalProductos = 0;

    if (query.length > 0) {
      $('#seccionVehiculos').hide();
    } else if ($('#buscarVehiculo').val().length === 0) {
      $('#seccionVehiculos').show();
    }

    $('.repuesto-card').each(function() {
      let card = $(this);
      let productName = card.attr('data-nombre');
      let rows = card.find('tbody tr.repuesto-row');
      let cardVisible = false;
      let cardTotalUnidades = 0;

      rows.each(function() {
        let row = $(this);
        let codigoBarras = row.find('.codigo-barras').text().toLowerCase();
        let ubicacion = row.find('.ubicacion-repuesto').text().toLowerCase();
        let marca = row.find('.marca-repuesto').text().toLowerCase();
        let modelo = row.find('.modelo-repuesto').text().toLowerCase();
        let categoria = row.find('.categoria-repuesto').text().toLowerCase();
        
        let match = productName.includes(query) || codigoBarras.includes(query) || ubicacion.includes(query) || marca.includes(query) || modelo.includes(query) || categoria.includes(query);
        
        if (match) {
          row.show();
          cardVisible = true;
          let cantidadStr = row.find('.cantidad-badge').text().trim();
          cardTotalUnidades += parseInt(cantidadStr) || 0;
        } else {
          row.hide();
        }
      });

      if (cardVisible) {
        card.show();
        totalProductos++;
        totalUnidades += cardTotalUnidades;
      } else {
        card.hide();
      }
    });

    $('#totalProductosRepuestos').text(totalProductos);
    $('#totalUnidadesRepuestos').text(totalUnidades);

    // RE-APLICAR PAGINACIÓN TRAS BÚSQUEDA
    aplicarPaginacionGlobal();
  });
});

// Toggle para mostrar placa e imperfecciones solo en "segunda" / "semi-nueva"
function toggleCamposSegunda() {
  let select = document.getElementById('estado_veh_stock');
  if (!select || select.selectedIndex === -1) return;
  let text = select.options[select.selectedIndex].text.toLowerCase();
  let divSegunda = document.getElementById('divSegunda');
  if (text.includes("segunda") || text.includes("semi-nueva") || text.includes("semi nueva") || select.value === "2") {
    divSegunda.style.display = 'flex';
  } else {
    divSegunda.style.display = 'none';
    divSegunda.querySelectorAll('input').forEach(input => input.value = '');
  }
}

// Guardar Vehículo
function guardarVehiculoRapido() {
  var form = document.getElementById('formVehiculoRapido');
  if (!form.checkValidity()) {
    form.reportValidity();
    return;
  }
  
  var idProd = document.getElementById('veh_nombre').value;
  if (!idProd) {
    Swal.fire('Atención', 'Debe seleccionar un producto válido de la lista de búsqueda.', 'warning');
    return;
  }
  
  var pMin = parseFloat(form.precio_minimo.value);
  var pMax = parseFloat(form.precio_maximo.value);
  if (pMin > pMax) {
      Swal.fire('Error', 'El Precio Mínimo no puede ser mayor al Precio Máximo.', 'warning');
      return;
  }
  
  var btn = document.getElementById('btnGuardarVehiculo');
  btn.disabled = true;
  btn.innerHTML = '<i class="fa-solid fa-spinner fa-spin me-2"></i>Guardando...';

  var formData = new FormData(form);
  
  fetch("{% url 'agregar_vehiculo_stock_directo' %}", {
    method: 'POST',
    body: formData,
    headers: { 'X-Requested-With': 'XMLHttpRequest' }
  })
  .then(res => res.json())
  .then(data => {
    if(data.success) {
      Swal.fire('Éxito', data.message, 'success').then(() => {
        try { bootstrap.Modal.getInstance(document.getElementById('modalStockVehiculo')).hide(); } catch(e) {}
        document.getElementById('formVehiculoRapido').reset();
        document.getElementById('veh_nombre').value = '';
        document.getElementById('vehiculo_search').value = '';
        cargarVehiculos(1, '');
        busquedaVehiculos = '';
        paginaVehiculos = 1;
      });
    } else {
      Swal.fire('Error', data.error, 'error');
      btn.disabled = false;
      btn.innerHTML = 'Guardar';
    }
  })
  .catch(err => {
    console.error(err);
    Swal.fire('Error', 'Ocurrió un error inesperado al guardar.', 'error');
    btn.disabled = false;
    btn.innerHTML = 'Guardar';
  });
}

// ==========================================
// EDICIÓN DE VEHÍCULOS
// ==========================================
function abrirModalEditarVehiculo(btn) {
  try {
    var idvehiculo = btn.getAttribute('data-idvehiculo');
    var idcompradetalle = btn.getAttribute('data-idcompradetalle');
    var idestadoproducto = btn.getAttribute('data-idestadoproducto');
    var seriemotor = btn.getAttribute('data-seriemotor');
    var seriechasis = btn.getAttribute('data-seriechasis');
    var anio = btn.getAttribute('data-anio');
    var imperfecciones = btn.getAttribute('data-imperfecciones');
    var placas = btn.getAttribute('data-placas');
    var preciocompra = btn.getAttribute('data-preciocompra');
    var preciopormayor = btn.getAttribute('data-preciopormayor');
    var preciominimo = btn.getAttribute('data-preciominimo');
    var preciomaximo = btn.getAttribute('data-preciomaximo');

    document.getElementById('edit_id_vehiculo').value = idvehiculo;
    document.getElementById('edit_idcompradetalle').value = idcompradetalle;
    document.getElementById('edit_serie_motor').value = seriemotor;
    document.getElementById('edit_serie_chasis').value = seriechasis;
    document.getElementById('edit_anio').value = anio;
    document.getElementById('edit_imperfecciones').value = imperfecciones;
    document.getElementById('edit_placas').value = placas;
    
    if (preciocompra) {
        document.getElementById('edit_precio_compra').value = parseFloat(preciocompra.replace(',', '.')).toFixed(2);
    }
    if (preciopormayor) {
        document.getElementById('edit_precio_por_mayor').value = parseFloat(preciopormayor.replace(',', '.')).toFixed(2);
    }
    if (preciominimo) {
        document.getElementById('edit_precio_minimo').value = parseFloat(preciominimo.replace(',', '.')).toFixed(2);
    }
    if (preciomaximo) {
        document.getElementById('edit_precio_maximo').value = parseFloat(preciomaximo.replace(',', '.')).toFixed(2);
    }

    var selectEstado = document.getElementById('edit_estado_vehiculo');
    selectEstado.value = idestadoproducto;
    toggleCamposSegundaEdit();

    var modalEl = document.getElementById('modalEditarVehiculo');
    document.body.appendChild(modalEl);
    var modal = new bootstrap.Modal(modalEl);
    modal.show();
  } catch(e) {
    alert("Error al abrir modal vehiculo: " + e.message);
  }
}

function toggleCamposSegundaEdit() {
  let select = document.getElementById('edit_estado_vehiculo');
  if (!select || select.selectedIndex === -1) return;
  let text = select.options[select.selectedIndex].text.toLowerCase();
  let divSegunda = document.getElementById('divSegundaEdit');
  if (text.includes("segunda") || text.includes("semi-nueva") || text.includes("semi nueva") || select.value === "2") {
    divSegunda.style.display = 'flex';
  } else {
    divSegunda.style.display = 'none';
  }
}

function guardarEdicionVehiculo() {
  var form = document.getElementById('formEditarVehiculo');
  if (!form.checkValidity()) {
    form.reportValidity();
    return;
  }
  
  var pMin = parseFloat(form.precio_minimo.value);
  var pMax = parseFloat(form.precio_maximo.value);
  if (pMin > pMax) {
      Swal.fire('Error', 'El Precio Mínimo no puede ser mayor al Precio Máximo.', 'warning');
      return;
  }
  
  var btn = document.getElementById('btnGuardarEdicionVehiculo');
  btn.disabled = true;
  btn.innerHTML = '<i class="fa-solid fa-spinner fa-spin me-2"></i>Guardando...';

  var formData = new FormData(form);
  
  fetch("{% url 'editar_vehiculo_stock' %}", {
    method: 'POST',
    body: formData,
    headers: { 'X-Requested-With': 'XMLHttpRequest' }
  })
  .then(res => res.json())
  .then(data => {
    if(data.success) {
      btn.disabled = false;
      btn.innerHTML = 'Guardar Cambios';
      Swal.fire('Éxito', data.message, 'success').then(() => {
        try { bootstrap.Modal.getInstance(document.getElementById('modalEditarVehiculo')).hide(); } catch(e) {}
        cargarVehiculos(paginaVehiculos, busquedaVehiculos);
      });
    } else {
      Swal.fire('Error', data.error, 'error');
      btn.disabled = false;
      btn.innerHTML = 'Guardar Cambios';
    }
  })
  .catch(err => {
    console.error(err);
    Swal.fire('Error', 'Ocurrió un error inesperado al guardar.', 'error');
    btn.disabled = false;
    btn.innerHTML = 'Guardar Cambios';
  });
}

function abrirModalEditarRepuesto(btn) {
  try {
    var idstock = btn.getAttribute('data-idstock');
    var idrepuestocomprado = btn.getAttribute('data-idrepuestocomprado');
    var idcompradetalle = btn.getAttribute('data-idcompradetalle');
    var ubicacion = btn.getAttribute('data-ubicacion');
    var preciocompra = btn.getAttribute('data-preciocompra');
    var preciopormayor = btn.getAttribute('data-preciopormayor');
    var preciominimo = btn.getAttribute('data-preciominimo');
    var preciomaximo = btn.getAttribute('data-preciomaximo');
    var cantidad = btn.getAttribute('data-cantidad');

    document.getElementById('edit_id_stock').value = idstock;
    document.getElementById('edit_id_repuesto_comprado').value = idrepuestocomprado;
    document.getElementById('edit_idcompradetalle_repuesto').value = idcompradetalle;
    document.getElementById('edit_ubicacion').value = ubicacion;
    
    document.getElementById('edit_repuesto_cantidad').value = cantidad;
    if (preciocompra) document.getElementById('edit_repuesto_precio_compra').value = parseFloat(preciocompra.replace(',', '.')).toFixed(2);
    if (preciopormayor) document.getElementById('edit_repuesto_precio_por_mayor').value = parseFloat(preciopormayor.replace(',', '.')).toFixed(2);
    if (preciominimo) document.getElementById('edit_repuesto_precio_minimo').value = parseFloat(preciominimo.replace(',', '.')).toFixed(2);
    if (preciomaximo) document.getElementById('edit_repuesto_precio_maximo').value = parseFloat(preciomaximo.replace(',', '.')).toFixed(2);
    
    var modalEl = document.getElementById('modalEditarRepuesto');
    document.body.appendChild(modalEl);
    var modal = new bootstrap.Modal(modalEl);
    modal.show();
  } catch(e) {
    alert("Error al abrir modal repuesto: " + e.message);
  }
}

function guardarEdicionRepuesto() {
  var form = document.getElementById('formEditarRepuesto');
  if (!form.checkValidity()) {
    form.reportValidity();
    return;
  }
  
  var pMin = parseFloat(form.precio_minimo.value);
  var pMax = parseFloat(form.precio_maximo.value);
  if (pMin > pMax) {
      Swal.fire('Error', 'El Precio Mínimo no puede ser mayor al Precio Máximo.', 'warning');
      return;
  }
  
  var btn = document.getElementById('btnGuardarEdicionRepuesto');
  btn.disabled = true;
  btn.innerHTML = '<i class="fa-solid fa-spinner fa-spin me-2"></i>Guardando...';

  var formData = new FormData(form);
  
  fetch("{% url 'editar_repuesto_stock' %}", {
    method: 'POST',
    body: formData,
    headers: { 'X-Requested-With': 'XMLHttpRequest' }
  })
  .then(res => res.json())
  .then(data => {
    if(data.success) {
      btn.disabled = false;
      btn.innerHTML = 'Guardar Cambios';
      Swal.fire('Éxito', data.message, 'success').then(() => {
        try { bootstrap.Modal.getInstance(document.getElementById('modalEditarRepuesto')).hide(); } catch(e) {}
        cargarRepuestos(paginaRepuestos, busquedaRepuestos);
      });
    } else {
      Swal.fire('Error', data.error, 'error');
      btn.disabled = false;
      btn.innerHTML = 'Guardar Cambios';
    }
  })
  .catch(err => {
    console.error(err);
    Swal.fire('Error', 'Ocurrió un error inesperado al guardar.', 'error');
    btn.disabled = false;
    btn.innerHTML = 'Guardar Cambios';
  });
}

// ==========================================
// FUNCIONES PARA DIVIDIR / MOVER STOCK
// ==========================================
function abrirModalMoverRepuesto(btn) {
  try {
    var idstock = btn.getAttribute('data-idstock');
    var ubicacion = btn.getAttribute('data-ubicacion');
    var cantidad = parseInt(btn.getAttribute('data-cantidad'));

    document.getElementById('mover_id_stock').value = idstock;
    document.getElementById('mover_cantidad_maxima').value = cantidad;
    document.getElementById('lbl_cantidad_maxima').innerText = cantidad;

    // Resetear formulario
    document.getElementById('mover_cantidad').value = '';
    document.getElementById('mover_cantidad').max = cantidad;
    document.getElementById('mover_ubicacion').value = '';

    var modalEl = document.getElementById('modalMoverStock');
    document.body.appendChild(modalEl);
    var modal = new bootstrap.Modal(modalEl);
    modal.show();
  } catch(e) {
    alert("Error al abrir modal mover: " + e.message);
  }
}

function guardarMoverStock() {
  var form = document.getElementById('formMoverStock');
  if (!form.checkValidity()) {
    form.reportValidity();
    return;
  }
  
  var cantidadMover = parseInt(document.getElementById('mover_cantidad').value);
  var cantidadMaxima = parseInt(document.getElementById('mover_cantidad_maxima').value);
  
  if (cantidadMover >= cantidadMaxima) {
    Swal.fire('Advertencia', 'Para mover la totalidad de este lote (' + cantidadMaxima + '), utiliza simplemente el botón de Editar (lápiz) y cambia la ubicación.', 'warning');
    return;
  }
  
  var btn = document.getElementById('btnGuardarMover');
  btn.disabled = true;
  btn.innerHTML = '<i class="fa-solid fa-spinner fa-spin me-2"></i>Moviendo...';

  var formData = new FormData(form);
  
  fetch("{% url 'mover_repuesto_stock' %}", {
    method: 'POST',
    body: formData,
    headers: { 'X-Requested-With': 'XMLHttpRequest' }
  })
  .then(res => res.json())
  .then(data => {
    if(data.success) {
      Swal.fire('Éxito', data.message, 'success').then(() => {
        try { bootstrap.Modal.getInstance(document.getElementById('modalMoverStock')).hide(); } catch(e) {}
        cargarRepuestos(paginaRepuestos, busquedaRepuestos);
      });
    } else {
      Swal.fire('Error', data.error, 'error');
      btn.disabled = false;
      btn.innerHTML = 'Mover Stock';
    }
  })
  .catch(err => {
    console.error(err);
    Swal.fire('Error', 'Ocurrió un error inesperado.', 'error');
    btn.disabled = false;
    btn.innerHTML = 'Mover Stock';
  });
}

// Guardar Repuesto
function guardarRepuestoRapido() {
  var form = document.getElementById('formRepuestoRapido');
  if (!form.checkValidity()) {
    form.reportValidity();
    return;
  }
  
  var idRep = document.getElementById('rep_nombre').value;
  if (!idRep) {
    Swal.fire('Atención', 'Debe seleccionar un repuesto válido de la lista de búsqueda.', 'warning');
    return;
  }
  
  var pMin = parseFloat(form.precio_minimo.value);
  var pMax = parseFloat(form.precio_maximo.value);
  if (pMin > pMax) {
      Swal.fire('Error', 'El Precio Mínimo no puede ser mayor al Precio Máximo.', 'warning');
      return;
  }
  
  var btn = document.getElementById('btnGuardarRepuesto');
  btn.disabled = true;
  btn.innerHTML = '<i class="fa-solid fa-spinner fa-spin me-2"></i>Guardando...';

  var formData = new FormData(form);
  
  fetch("{% url 'agregar_repuesto_stock_directo' %}", {
    method: 'POST',
    body: formData,
    headers: { 'X-Requested-With': 'XMLHttpRequest' }
  })
  .then(res => res.json())
  .then(data => {
    if(data.success) {
      Swal.fire('Éxito', data.message, 'success').then(() => {
        try { bootstrap.Modal.getInstance(document.getElementById('modalStockRepuesto')).hide(); } catch(e) {}
        document.getElementById('formRepuestoRapido').reset();
        document.getElementById('rep_nombre').value = '';
        document.getElementById('repuesto_search').value = '';
        cargarRepuestos(1, '');
        busquedaRepuestos = '';
        paginaRepuestos = 1;
      });
    } else {
      Swal.fire('Error', data.error, 'error');
      btn.disabled = false;
      btn.innerHTML = 'Guardar';
    }
  })
  .catch(err => {
    console.error(err);
    Swal.fire('Error', 'Ocurrió un error inesperado al guardar.', 'error');
    btn.disabled = false;
    btn.innerHTML = 'Guardar';
  });
}


// ============================================================
// SERVER-SIDE PROCESSING — AJAX LOAD SYSTEM
// ============================================================

// Estado global de paginación y búsqueda
let paginaVehiculos = 1;
let busquedaVehiculos = '';
let paginaRepuestos = 1;
let busquedaRepuestos = '';

// ── Función helper para generar HTML de paginación con puntos suspensivos ──
function generarHtmlPaginacion(paginaActual, totalPaginas, accionJs) {
  var maxPagesToShow = 5;
  var html = '';
  if (totalPaginas <= 1) return '';

  var startPage = Math.max(1, paginaActual - Math.floor(maxPagesToShow / 2));
  var endPage = Math.min(totalPaginas, startPage + maxPagesToShow - 1);
  
  if (endPage - startPage + 1 < maxPagesToShow) {
    startPage = Math.max(1, endPage - maxPagesToShow + 1);
  }

  html += '<nav><ul class="pagination pagination-sm mb-0">';
  
  html += '<li class="page-item ' + (paginaActual === 1 ? 'disabled' : '') + '">' +
    '<a class="page-link" href="#" onclick="event.preventDefault();' + accionJs.replace(/__PAGE__/g, paginaActual - 1) + '">Anterior</a></li>';

  if (startPage > 1) {
    html += '<li class="page-item"><a class="page-link" href="#" onclick="event.preventDefault();' + accionJs.replace(/__PAGE__/g, 1) + '">1</a></li>';
    if (startPage > 2) {
      html += '<li class="page-item disabled"><span class="page-link">...</span></li>';
    }
  }

  for (var i = startPage; i <= endPage; i++) {
    html += '<li class="page-item ' + (i === paginaActual ? 'active' : '') + '">' +
      '<a class="page-link" href="#" onclick="event.preventDefault();' + accionJs.replace(/__PAGE__/g, i) + '">' + i + '</a></li>';
  }

  if (endPage < totalPaginas) {
    if (endPage < totalPaginas - 1) {
      html += '<li class="page-item disabled"><span class="page-link">...</span></li>';
    }
    html += '<li class="page-item"><a class="page-link" href="#" onclick="event.preventDefault();' + accionJs.replace(/__PAGE__/g, totalPaginas) + '">' + totalPaginas + '</a></li>';
  }

  html += '<li class="page-item ' + (paginaActual === totalPaginas ? 'disabled' : '') + '">' +
    '<a class="page-link" href="#" onclick="event.preventDefault();' + accionJs.replace(/__PAGE__/g, paginaActual + 1) + '">Siguiente</a></li>';

  html += '</ul></nav>';
  return html;
}

// ── Paginación reutilizable ──
function renderPaginacion(contenedorId, paginaActual, totalPaginas, fnCargar, busquedaActual) {
  var contenedor = document.getElementById(contenedorId);
  if (!contenedor) return;
  if (totalPaginas <= 1) { contenedor.innerHTML = ''; return; }
  
  var cleanSearch = busquedaActual ? busquedaActual.replace(/'/g, '') : '';
  var onClickFnStr = fnCargar.name + '(__PAGE__, \'' + cleanSearch + '\')';
  
  contenedor.innerHTML = generarHtmlPaginacion(paginaActual, totalPaginas, onClickFnStr);
}

// ── Paginación interna de cada grupo ──
function cambiarPaginaInterna(groupId, page, totalPages) {
  var rows = document.querySelectorAll('.inner-row-' + groupId);
  rows.forEach(function(r) { r.style.display = 'none'; });
  
  var pageRows = document.querySelectorAll('.inner-row-' + groupId + '.inner-page-' + page);
  pageRows.forEach(function(r) { r.style.display = ''; });
  
  var container = document.getElementById('pag-inner-' + groupId);
  if (container && totalPages) {
    var onClickFnStr = 'cambiarPaginaInterna(\'' + groupId + '\', __PAGE__, ' + totalPages + ')';
    container.innerHTML = generarHtmlPaginacion(page, totalPages, onClickFnStr);
  }
}

// ── Cargar Vehículos ──
function cargarVehiculos(page, search) {
  page = page || 1;
  search = (search === undefined || search === null) ? '' : search;
  paginaVehiculos = page;
  busquedaVehiculos = search;
  var contenedor = document.getElementById('contenedorGruposVehiculos');
  if (!contenedor) return;
  contenedor.innerHTML = '<div class="text-center py-4"><div class="spinner-border text-success" role="status"></div><p class="mt-2 text-muted">Cargando...</p></div>';

  fetch('/stock/api/vehiculos/?page=' + page + '&search=' + encodeURIComponent(search))
    .then(function(res) { return res.json(); })
    .then(function(data) {
      document.getElementById('totalProductosVehiculos').textContent = data.total_grupos;
      document.getElementById('totalUnidadesVehiculos').textContent = data.total_unidades;
      contenedor.innerHTML = '';
      if (!data.grupos || data.grupos.length === 0) {
        contenedor.innerHTML = '<div class="alert alert-info text-center"><i class="fa-solid fa-info-circle fa-2x mb-2"></i><p class="mb-0">No hay vehículos en stock</p></div>';
        document.getElementById('paginacionGruposVehiculos').innerHTML = '';
        return;
      }
      data.grupos.forEach(function(grupo) {
        contenedor.innerHTML += renderGrupoVehiculo(grupo);
      });
      renderPaginacion('paginacionGruposVehiculos', data.pagina_actual, data.total_paginas, cargarVehiculos, search);
    })
    .catch(function() {
      contenedor.innerHTML = '<div class="alert alert-danger text-center">Error al cargar el inventario de vehículos.</div>';
    });
}

function renderGrupoVehiculo(grupo) {
  var itemsPerPage = 10;
  var totalPages = Math.ceil(grupo.detalles.length / itemsPerPage);
  var groupId = 'veh-grp-' + Math.random().toString(36).substr(2, 9);

  var filas = grupo.detalles.map(function(det, i) {
    var page = Math.floor(i / itemsPerPage) + 1;
    var displayStyle = page === 1 ? '' : 'display: none;';
    var sitClass = det.situacion === 'DISPONIBLE' ? 'bg-success'
      : det.situacion === 'RETENIDO' ? 'bg-danger'
      : det.situacion.indexOf('RESERVADO') >= 0 ? 'bg-info' : 'bg-warning';
    var imperfHtml = det.imperfecciones === 'Ninguna'
      ? '<span class="text-success"><i class="fa-solid fa-check-circle me-1"></i>' + det.imperfecciones + '</span>'
      : '<span class="text-warning"><i class="fa-solid fa-exclamation-circle me-1"></i>' + det.imperfecciones + '</span>';
    var pc = parseFloat(det.precio_compra || 0).toFixed(2);
    var pmayor = parseFloat(det.precio_por_mayor || 0).toFixed(2);
    var pm = parseFloat(det.precio_minimo || 0).toFixed(2);
    var px = parseFloat(det.precio_maximo || 0).toFixed(2);
    return '<tr class="vehiculo-row inner-row-' + groupId + ' inner-page-' + page + '" style="' + displayStyle + '">' +
      '<td class="text-center fw-semibold">' + (i + 1) + '</td>' +
      '<td><code class="text-dark serie-motor">' + (det.serie_motor || '-') + '</code></td>' +
      '<td><code class="text-dark serie-chasis">' + (det.serie_chasis || '-') + '</code></td>' +
      '<td class="text-center"><span class="badge bg-light text-dark border anio">' + (det.anio || '-') + '</span></td>' +
      '<td class="text-center"><span class="badge bg-info">' + det.estado + '</span></td>' +
      '<td class="text-center"><span class="badge ' + sitClass + '">' + det.situacion + '</span></td>' +
      '<td>' + imperfHtml + '</td>' +
      (ROL_USUARIO === 1 || ROL_USUARIO === 5 ? '<td class="text-end fw-semibold text-danger">S/ ' + pc + '</td>' : '') +
      '<td class="text-end fw-semibold text-primary">S/ ' + pmayor + '</td>' +
      '<td class="text-end fw-semibold text-success">S/ ' + pm + '</td>' +
      '<td class="text-end fw-semibold" style="color:#6f42c1;">S/ ' + px + '</td>' +
      '<td class="text-center"><span class="badge bg-success rounded-pill fs-6 cantidad-badge">' + det.cantidad + '</span></td>' +
      '<td class="text-center">' +
        '<button class="btn btn-sm btn-outline-primary rounded-circle" onclick="abrirModalEditarVehiculo(this)"' +
        ' data-idvehiculo="' + det.id_vehiculo + '"' +
        ' data-idcompradetalle="' + det.idcompradetalle + '"' +
        ' data-idestadoproducto="' + det.idestadoproducto + '"' +
        ' data-seriemotor="' + (det.serie_motor || '') + '"' +
        ' data-seriechasis="' + (det.serie_chasis || '') + '"' +
        ' data-anio="' + (det.anio || '') + '"' +
        ' data-imperfecciones="' + (det.imperfecciones || '') + '"' +
        ' data-placas="' + (det.placas || '') + '"' +
        ' data-preciocompra="' + pc + '"' +
        ' data-preciopormayor="' + pmayor + '"' +
        ' data-preciominimo="' + pm + '"' +
        ' data-preciomaximo="' + px + '"' +
        ' title="Editar"><i class="fa-solid fa-pen"></i></button>' +
      '</td></tr>';
  }).join('');

  var paginationHtml = '';
  if (totalPages > 1) {
    var onClickFnStr = 'cambiarPaginaInterna(\'' + groupId + '\', __PAGE__, ' + totalPages + ')';
    paginationHtml = '<div class="d-flex justify-content-center py-2 bg-light border-top" id="pag-inner-' + groupId + '">' + generarHtmlPaginacion(1, totalPages, onClickFnStr) + '</div>';
  }

  return '<div class="card mb-3 border-success shadow-sm">' +
    '<div class="card-header bg-success text-white d-flex justify-content-between align-items-center">' +
    '<h6 class="mb-0 fw-bold"><i class="fa-solid fa-tag me-2"></i>' + grupo.nombre + '</h6>' +
    '<span class="badge bg-white text-success fw-bold fs-6"><i class="fa-solid fa-boxes-stacked me-1"></i>Stock: ' + grupo.cantidad_total + '</span>' +
    '</div><div class="card-body p-0"><div class="table-responsive">' +
    '<table class="table table-hover table-striped align-middle mb-0"><thead class="table-light"><tr>' +
    '<th class="text-center">#</th>' +
    '<th><i class="fa-solid fa-gear me-1"></i>Serie Motor</th>' +
    '<th><i class="fa-solid fa-car me-1"></i>Serie Chasis</th>' +
    '<th class="text-center"><i class="fa-solid fa-calendar-days me-1"></i>Año</th>' +
    '<th class="text-center"><i class="fa-solid fa-circle-check me-1"></i>Estado</th>' +
    '<th class="text-center"><i class="fa-solid fa-location-dot me-1"></i>Situación</th>' +
    '<th><i class="fa-solid fa-triangle-exclamation me-1"></i>Imperfecciones</th>' +
    (ROL_USUARIO === 1 || ROL_USUARIO === 5 ? '<th class="text-end"><i class="fa-solid fa-arrow-down me-1"></i>P. Compra</th>' : '') +
    '<th class="text-end"><i class="fa-solid fa-arrow-up me-1"></i>P. X Mayor</th>' +
    '<th class="text-end"><i class="fa-solid fa-arrow-up me-1"></i>P. Cash</th>' +
    '<th class="text-end"><i class="fa-solid fa-arrow-up-right-dots me-1"></i>P. Lista</th>' +
    '<th class="text-center"><i class="fa-solid fa-hashtag me-1"></i>Cant.</th>' +
    '<th class="text-center"><i class="fa-solid fa-cogs me-1"></i>Acciones</th>' +
    '</tr></thead><tbody>' + filas + '</tbody>' +
    '<tfoot class="table-secondary fw-bold"><tr><td colspan="' + (ROL_USUARIO === 1 || ROL_USUARIO === 5 ? 10 : 9) + '" class="text-end">SUBTOTAL:</td><td></td>' +
    '<td class="text-center"><span class="badge bg-success fs-6">' + grupo.cantidad_total + '</span></td><td></td>' +
    '</tr></tfoot></table></div>' + paginationHtml + '</div></div>';
}

// ── Cargar Repuestos ──
function cargarRepuestos(page, search) {
  page = page || 1;
  search = (search === undefined || search === null) ? '' : search;
  paginaRepuestos = page;
  busquedaRepuestos = search;
  var contenedor = document.getElementById('contenedorGruposRepuestos');
  if (!contenedor) return;
  contenedor.innerHTML = '<div class="text-center py-4"><div class="spinner-border text-primary" role="status"></div><p class="mt-2 text-muted">Cargando...</p></div>';

  fetch('/stock/api/repuestos/?page=' + page + '&search=' + encodeURIComponent(search))
    .then(function(res) { return res.json(); })
    .then(function(data) {
      document.getElementById('totalProductosRepuestos').textContent = data.total_grupos;
      document.getElementById('totalUnidadesRepuestos').textContent = data.total_unidades;
      contenedor.innerHTML = '';
      if (!data.grupos || data.grupos.length === 0) {
        contenedor.innerHTML = '<div class="alert alert-info text-center"><i class="fa-solid fa-info-circle fa-2x mb-2"></i><p class="mb-0">No hay repuestos en stock</p></div>';
        document.getElementById('paginacionGruposRepuestos').innerHTML = '';
        return;
      }
      data.grupos.forEach(function(grupo) {
        contenedor.innerHTML += renderGrupoRepuesto(grupo);
      });
      renderPaginacion('paginacionGruposRepuestos', data.pagina_actual, data.total_paginas, cargarRepuestos, search);
    })
    .catch(function() {
      contenedor.innerHTML = '<div class="alert alert-danger text-center">Error al cargar el inventario de repuestos.</div>';
    });
}

function renderGrupoRepuesto(grupo) {
  var pctBar = grupo.porcentaje_stock || 0;
  var saludClass = grupo.estado_salud === 'critico' ? 'bg-danger pulse-animation'
    : grupo.estado_salud === 'exceso' ? 'bg-warning' : 'bg-success';

  var itemsPerPage = 10;
  var totalPages = Math.ceil(grupo.detalles.length / itemsPerPage);
  var groupId = 'rep-grp-' + Math.random().toString(36).substr(2, 9);

  var filas = grupo.detalles.map(function(det, i) {
    var page = Math.floor(i / itemsPerPage) + 1;
    var displayStyle = page === 1 ? '' : 'display: none;';
    var codigoHtml = (det.codigo_barras && det.codigo_barras !== 'N/A')
      ? '<span class="badge bg-secondary mb-1 codigo-barras"><i class="fa-solid fa-barcode me-1"></i>' + det.codigo_barras + '</span><br>'
      : '<span class="d-none codigo-barras">N/A</span>';
    var pc = parseFloat(det.precio_compra || 0).toFixed(2);
    var pmayor = parseFloat(det.precio_por_mayor || 0).toFixed(2);
    var pm = parseFloat(det.precio_minimo || 0).toFixed(2);
    var px = parseFloat(det.precio_maximo || 0).toFixed(2);
    return '<tr class="repuesto-row inner-row-' + groupId + ' inner-page-' + page + '" style="' + displayStyle + '">' +
      '<td class="text-center fw-semibold align-middle">' + (i + 1) + '</td>' +
      '<td class="align-middle">' + codigoHtml +
        '<div class="small mt-1"><strong>Cat:</strong> <span class="categoria-repuesto">' + det.categoria + '</span> | ' +
        '<strong>Marca:</strong> <span class="marca-repuesto">' + det.marca + '</span> | ' +
        '<strong>Mod/Ref:</strong> <span class="modelo-repuesto">' + det.modelo + '</span></div></td>' +
      '<td class="ubicacion-repuesto align-middle">' + det.ubicacion + '</td>' +
      '<td class="align-middle"><div class="small fw-semibold">' +
        (ROL_USUARIO === 1 || ROL_USUARIO === 5 ? '<span>C: S/ ' + pc + '</span><br>' : '') +
        '<span class="text-muted mt-1 d-inline-block">P. Mayor: S/ ' + pmayor + ' | P. Cash: S/ ' + pm + ' | P. Lista: S/ ' + px + '</span>' +
      '</div></td>' +
      '<td class="text-center align-middle"><span class="badge bg-primary rounded-pill fs-6 cantidad-badge">' + det.cantidad + '</span></td>' +
      '<td class="text-center align-middle">' +
        '<button class="btn btn-sm btn-outline-info rounded-circle me-1" onclick="abrirModalMoverRepuesto(this)"' +
        ' data-idstock="' + det.id_stock + '"' +
        ' data-idrepuestocomprado="' + det.id_repuesto_comprado + '"' +
        ' data-idcompradetalle="' + det.idcompradetalle + '"' +
        ' data-ubicacion="' + (det.ubicacion || '') + '"' +
        ' data-cantidad="' + det.cantidad + '"' +
        ' title="Dividir / Mover Lote"><i class="fa-solid fa-arrows-split-up-and-left"></i></button>' +
        '<button class="btn btn-sm btn-outline-primary rounded-circle" onclick="abrirModalEditarRepuesto(this)"' +
        ' data-idstock="' + det.id_stock + '"' +
        ' data-idrepuestocomprado="' + det.id_repuesto_comprado + '"' +
        ' data-idcompradetalle="' + det.idcompradetalle + '"' +
        ' data-codigobarras="' + (det.codigo_barras || 'N/A') + '"' +
        ' data-ubicacion="' + (det.ubicacion || '') + '"' +
        ' data-preciocompra="' + pc + '"' +
        ' data-preciopormayor="' + pmayor + '"' +
        ' data-preciominimo="' + pm + '"' +
        ' data-preciomaximo="' + px + '"' +
        ' data-cantidad="' + det.cantidad + '"' +
        ' title="Editar Stock"><i class="fa-solid fa-pen"></i></button>' +
      '</td></tr>';
  }).join('');

  var paginationHtml = '';
  if (totalPages > 1) {
    var onClickFnStr = 'cambiarPaginaInterna(\'' + groupId + '\', __PAGE__, ' + totalPages + ')';
    paginationHtml = '<div class="d-flex justify-content-center py-2 bg-light border-top" id="pag-inner-' + groupId + '">' + generarHtmlPaginacion(1, totalPages, onClickFnStr) + '</div>';
  }

  return '<div class="card mb-3 border-primary shadow-sm">' +
    '<div class="card-header bg-primary text-white d-flex justify-content-between align-items-center">' +
    '<h6 class="mb-0 fw-bold"><i class="fa-solid fa-tag me-2"></i>' + grupo.nombre + '</h6>' +
    '<div class="d-flex flex-column align-items-end" style="min-width:250px;">' +
    '<div class="d-flex justify-content-between w-100 mb-1 align-items-center">' +
    '<span class="text-white fw-bold me-2"><i class="fa-solid fa-boxes-stacked me-1"></i>Stock: ' + grupo.cantidad_total + '</span>' +
    '<span class="badge bg-light text-primary" style="font-size:0.70rem;">Mín: ' + grupo.stock_minimo + ' | Máx: ' + grupo.stock_maximo + '</span>' +
    '</div>' +
    '<div class="progress w-100 shadow-sm" style="height:10px;background-color:rgba(255,255,255,0.3);border-radius:10px;overflow:hidden;">' +
    '<div class="progress-bar progress-bar-striped progress-bar-animated ' + saludClass + '" role="progressbar" style="width:' + pctBar + '%;" aria-valuenow="' + pctBar + '" aria-valuemin="0" aria-valuemax="100"></div>' +
    '</div></div></div>' +
    '<div class="card-body p-0"><div class="table-responsive">' +
    '<table class="table table-hover table-striped align-middle mb-0"><thead class="table-light"><tr>' +
    '<th class="text-center align-middle" style="width:5%;">#</th>' +
    '<th class="align-middle" style="width:35%;"><i class="fa-solid fa-tags me-1"></i>DETALLES DEL REPUESTO</th>' +
    '<th class="align-middle" style="width:20%;"><i class="fa-solid fa-location-dot me-1"></i>UBICACIÓN</th>' +
    '<th class="align-middle" style="width:20%;"><i class="fa-solid fa-money-bill-wave me-1"></i>PRECIOS (REF.)</th>' +
    '<th class="text-center align-middle" style="width:10%;"><i class="fa-solid fa-hashtag me-1"></i>STOCK</th>' +
    '<th class="text-center align-middle" style="width:10%;"><i class="fa-solid fa-gears me-1"></i>ACCIONES</th>' +
    '</tr></thead><tbody>' + filas + '</tbody>' +
    '<tfoot class="table-secondary fw-bold"><tr><td colspan="4" class="text-end pe-4 align-middle">SUBTOTAL:</td>' +
    '<td class="text-center align-middle"><span class="badge bg-primary fs-6">' + grupo.cantidad_total + '</span></td><td></td>' +
    '</tr></tfoot></table></div>' + paginationHtml + '</div></div>';
}

// ── Exportar Excel (backend) ──
function exportarExcel() {
  window.location.href = '{% url "exportar_excel_stock" %}';
}

// DATA ARRAYS Y LOGICA DE AUTOCOMPLETE BUSQUEDA RAPIDA
const vehiculosData = [
  {% for p in productos_catalogo %}
  { id: "{{ p.idproducto }}", text: "{{ p.nomproducto|escapejs }}" },
  {% endfor %}
];

const repuestosData = [
  {% for r in catalogo_repuestos %}
  { id: "{{ r.id_repuesto }}", text: "{{ r.nombre|escapejs }} ({% if r.idmarca %}{{ r.idmarca.nombremarca|escapejs }}{% else %}Sin Marca{% endif %} - {% if r.modelo_referencia %}{{ r.modelo_referencia|escapejs }}{% else %}Sin Modelo{% endif %} - {% if r.id_categoria_repuesto %}{{ r.id_categoria_repuesto.nomcategoria|escapejs }}{% else %}Sin Categoría{% endif %})" },
  {% endfor %}
];

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

  // Limpiar al cambiar si no se seleccionó nada
  input.addEventListener('focus', function () {
    if (this.value && !hidden.value) {
      this.value = '';
    }
  });
}

function toggleAutocomplete(inputId, resultsId) {
  const input = document.getElementById(inputId);
  const results = document.getElementById(resultsId);

  let data = [];
  let hiddenId = '';

  if (inputId === 'vehiculo_search') {
    data = vehiculosData;
    hiddenId = 'veh_nombre';
  } else if (inputId === 'repuesto_search') {
    data = repuestosData;
    hiddenId = 'rep_nombre';
  }

  if (results.style.display === 'block') {
    results.style.display = 'none';
    return;
  }

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

// Inicializar autocompletes al cargar el DOM
document.addEventListener('DOMContentLoaded', function () {
  setupAutocomplete('vehiculo_search', 'vehiculo_results', vehiculosData, 'veh_nombre');
  setupAutocomplete('repuesto_search', 'repuesto_results', repuestosData, 'rep_nombre');
});

