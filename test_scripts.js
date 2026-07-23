
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
  
  fetch("// url 'agregar_vehiculo_stock_directo' //", {
    method: 'POST',
    body: formData,
    headers: { 'X-Requested-With': 'XMLHttpRequest' }
  })
  .then(res => res.json())
  .then(data => {
    if(data.success) {
      Swal.fire('Éxito', data.message, 'success').then(() => location.reload());
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
  var idvehiculo = btn.getAttribute('data-idvehiculo');
  var idcompradetalle = btn.getAttribute('data-idcompradetalle');
  var idestadoproducto = btn.getAttribute('data-idestadoproducto');
  var seriemotor = btn.getAttribute('data-seriemotor');
  var seriechasis = btn.getAttribute('data-seriechasis');
  var anio = btn.getAttribute('data-anio');
  var imperfecciones = btn.getAttribute('data-imperfecciones');
  var placas = btn.getAttribute('data-placas');
  var preciocompra = btn.getAttribute('data-preciocompra');
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
  if (preciominimo) {
      document.getElementById('edit_precio_minimo').value = parseFloat(preciominimo.replace(',', '.')).toFixed(2);
  }
  if (preciomaximo) {
      document.getElementById('edit_precio_maximo').value = parseFloat(preciomaximo.replace(',', '.')).toFixed(2);
  }

  var selectEstado = document.getElementById('edit_estado_vehiculo');
  selectEstado.value = idestadoproducto;
  toggleCamposSegundaEdit();

  var modal = new bootstrap.Modal(document.getElementById('modalEditarVehiculo'));
  modal.show();
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
  
  fetch("// url 'editar_vehiculo_stock' //", {
    method: 'POST',
    body: formData,
    headers: { 'X-Requested-With': 'XMLHttpRequest' }
  })
  .then(res => res.json())
  .then(data => {
    if(data.success) {
      Swal.fire('Éxito', data.message, 'success').then(() => location.reload());
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
  var idstock = btn.getAttribute('data-idstock');
  var idrepuestocomprado = btn.getAttribute('data-idrepuestocomprado');
  var idcompradetalle = btn.getAttribute('data-idcompradetalle');
  var ubicacion = btn.getAttribute('data-ubicacion');
  var preciocompra = btn.getAttribute('data-preciocompra');
  var preciominimo = btn.getAttribute('data-preciominimo');
  var preciomaximo = btn.getAttribute('data-preciomaximo');
  var cantidad = btn.getAttribute('data-cantidad');

  document.getElementById('edit_id_stock').value = idstock;
  document.getElementById('edit_id_repuesto_comprado').value = idrepuestocomprado;
  document.getElementById('edit_idcompradetalle_repuesto').value = idcompradetalle;
  document.getElementById('edit_ubicacion').value = ubicacion;
  
  document.getElementById('edit_repuesto_cantidad').value = cantidad;
  if (preciocompra) document.getElementById('edit_repuesto_precio_compra').value = parseFloat(preciocompra.replace(',', '.')).toFixed(2);
  if (preciominimo) document.getElementById('edit_repuesto_precio_minimo').value = parseFloat(preciominimo.replace(',', '.')).toFixed(2);
  if (preciomaximo) document.getElementById('edit_repuesto_precio_maximo').value = parseFloat(preciomaximo.replace(',', '.')).toFixed(2);
  
  var modal = new bootstrap.Modal(document.getElementById('modalEditarRepuesto'));
  modal.show();
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
  
  fetch("// url 'editar_repuesto_stock' //", {
    method: 'POST',
    body: formData,
    headers: { 'X-Requested-With': 'XMLHttpRequest' }
  })
  .then(res => res.json())
  .then(data => {
    if(data.success) {
      Swal.fire('Éxito', data.message, 'success').then(() => location.reload());
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
  
  fetch("// url 'agregar_repuesto_stock_directo' //", {
    method: 'POST',
    body: formData,
    headers: { 'X-Requested-With': 'XMLHttpRequest' }
  })
  .then(res => res.json())
  .then(data => {
    if(data.success) {
      Swal.fire('Éxito', data.message, 'success').then(() => location.reload());
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

// Función para imprimir
function imprimirStock() {
  window.print();
}

// Función para exportar (puedes implementar exportación a Excel)
function exportarExcel() {
  Swal.fire({
    title: 'Exportar a Excel',
    text: '¿Deseas exportar el stock a Excel?',
    icon: 'question',
    showCancelButton: true,
    confirmButtonColor: '#3085d6',
    cancelButtonColor: '#d33',
    confirmButtonText: 'Sí, exportar',
    cancelButtonText: 'Cancelar'
  }).then((result) => {
    if (result.isConfirmed) {
      Swal.fire(
        'Exportado!',
        'El archivo se ha descargado correctamente.',
        'success'
      );
    }
  });
}

// DATA ARRAYS Y LOGICA DE AUTOCOMPLETE BUSQUEDA RAPIDA
const vehiculosData = [
  // for p in productos_catalogo //
  { id: "{{ p.idproducto }}", text: "{{ p.nomproducto|escapejs }}" },
  // endfor //
];

const repuestosData = [
  // for r in catalogo_repuestos //
  { id: "{{ r.id_repuesto }}", text: "{{ r.nombre|escapejs }} (// if r.idmarca //{{ r.idmarca.nombremarca|escapejs }}// else //Sin Marca// endif // - // if r.modelo_referencia //{{ r.modelo_referencia|escapejs }}// else //Sin Modelo// endif // - // if r.id_categoria_repuesto //{{ r.id_categoria_repuesto.nomcategoria|escapejs }}// else //Sin Categoría// endif //)" },
  // endfor //
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
