
// ============================================================
const ROL_USUARIO = parseInt("{{ request.session.idtipousuario }}") || 0;
// ============================================================
// INICIALIZACIÓN Y BUSCADORES CON DEBOUNCE
// ============================================================
document.addEventListener('DOMContentLoaded', function () {
  // Cargar inventario desde el servidor al entrar
  cargarVehiculos(1, '');
  cargarRepuestos(1, '');

  // Buscador de vehículos — debounce 400ms
  var debounceVehiculo = null;
  var inputVehiculo = document.getElementById('buscarVehiculo');
  if (inputVehiculo) {
    inputVehiculo.addEventListener('input', function () {
      clearTimeout(debounceVehiculo);
      var val = this.value.trim();
      debounceVehiculo = setTimeout(function () {
        cargarVehiculos(1, val);
      }, 400);
    });
  }

  // Buscador de repuestos — debounce 400ms
  var debounceRepuesto = null;
  var inputRepuesto = document.getElementById('buscarRepuesto');
  if (inputRepuesto) {
    inputRepuesto.addEventListener('input', function () {
      clearTimeout(debounceRepuesto);
      var val = this.value.trim();
      debounceRepuesto = setTimeout(function () {
        cargarRepuestos(1, val);
      }, 400);
    });
  }

  // ══════════════════════════════════════════════════════════════════════════
  // PESTAÑA 2 — Búsqueda Global de Stock Multi-Sucursal
  // ══════════════════════════════════════════════════════════════════════════

  var globalSearchDebounce = null;
  var globalSearchInputEl  = document.getElementById('globalSearchInput');
  var globalSearchBtnEl    = document.getElementById('globalSearchBtn');
  var globalResultsEl      = document.getElementById('globalSearchResults');
  var globalSpinnerEl      = document.getElementById('globalSearchSpinner');
  var globalEmptyEl        = document.getElementById('globalSearchEmpty');

  // Función principal de búsqueda
  function ejecutarBusquedaGlobal() {
    var q = globalSearchInputEl ? globalSearchInputEl.value.trim() : '';
    if (q.length < 3) {
      mostrarAlertaGlobal('warning', 'Ingrese al menos 3 caracteres para buscar.');
      return;
    }

    // Mostrar spinner, ocultar el resto
    if (globalSpinnerEl)  globalSpinnerEl.classList.remove('d-none');
    if (globalEmptyEl)    globalEmptyEl.classList.add('d-none');
    if (globalResultsEl)  globalResultsEl.classList.add('d-none');
    if (globalResultsEl)  globalResultsEl.innerHTML = '';
    if (globalSearchBtnEl) { globalSearchBtnEl.disabled = true; }

    fetch('/stock/api/buscar-global/?search=' + encodeURIComponent(q))
      .then(function(resp) { return resp.json(); })
      .then(function(data) {
        if (globalSpinnerEl) globalSpinnerEl.classList.add('d-none');
        if (globalSearchBtnEl) globalSearchBtnEl.disabled = false;

        if (data.error) {
          mostrarAlertaGlobal('warning', data.error);
          if (globalEmptyEl) globalEmptyEl.classList.remove('d-none');
          return;
        }

        if (!data.grupos || data.grupos.length === 0) {
          if (globalEmptyEl) {
            globalEmptyEl.classList.remove('d-none');
            globalEmptyEl.querySelector('p').textContent = 'Sin resultados para "' + q + '" en ninguna sucursal.';
          }
          return;
        }

        // Renderizar resultados
        var html = '<div class="mb-3"><span class="badge bg-secondary fs-6">' +
                   data.total + ' resultado(s) encontrado(s)</span></div>';

        data.grupos.forEach(function(grupo) {
          var badgeSucursal = grupo.es_propia
            ? '<span class="badge ms-2" style="background:#198754;">Tu sucursal</span>'
            : '';
          var bgHeader = grupo.es_propia
            ? 'background: linear-gradient(90deg, #19875420, #0d6efd10);'
            : 'background: linear-gradient(90deg, #0d6efd15, #0dcaf015);';
          var borderColor = grupo.es_propia ? '#198754' : '#0d6efd';

          html += '<div class="card shadow-sm border-0 mb-4" style="border-radius: 14px; border-left: 4px solid ' + borderColor + ' !important;">';
          html += '  <div class="card-header border-0 py-2 px-3 d-flex align-items-center" style="' + bgHeader + 'border-radius: 14px 14px 0 0;">';
          html += '    <i class="fa-solid fa-building me-2" style="color:' + borderColor + ';"></i>';
          html += '    <strong style="color:' + borderColor + ';">' + grupo.sucursal + '</strong>' + badgeSucursal;
          html += '  </div>';
          html += '  <div class="card-body p-0">';
          html += '  <div class="table-responsive">';
          html += '    <table class="table table-hover mb-0" style="font-size:0.9rem;">';
          html += '      <thead class="table-light"><tr>';
          html += '        <th style="min-width:180px;">Producto / Repuesto</th>';
          html += '        <th>Detalle</th>';
          html += '        <th>Almacén</th>';
          html += '        <th class="text-center">Cantidad</th>';
          if (!grupo.es_propia) {
            html += '      <th class="text-center">Acción</th>';
          }
          html += '      </tr></thead>';
          html += '      <tbody>';

          grupo.items.forEach(function(item) {
            var tipoIcon = item.tipo === 'vehiculo'
              ? '<i class="fa-solid fa-motorcycle text-success me-1"></i>'
              : '<i class="fa-solid fa-wrench text-primary me-1"></i>';
            html += '<tr>';
            html += '  <td class="align-middle fw-semibold">' + tipoIcon + item.nombre + '</td>';
            html += '  <td class="align-middle text-muted small">' + item.detalle + '</td>';
            html += '  <td class="align-middle">' + item.almacen + '</td>';
            html += '  <td class="align-middle text-center">';
            html += '    <span class="badge bg-success fs-6" style="min-width:36px;">' + item.cantidad + '</span>';
            html += '  </td>';
            if (!grupo.es_propia) {
              var dataAttrs = 'data-idstock="' + item.id_stock + '" ' +
                              'data-tipo="' + item.tipo + '" ' +
                              'data-nombre="' + item.nombre.replace(/"/g,'&quot;') + '" ' +
                              'data-detalle="' + item.detalle.replace(/"/g,'&quot;') + '" ' +
                              'data-origen="' + grupo.sucursal.replace(/"/g,'&quot;') + ' — ' + item.almacen.replace(/"/g,'&quot;') + '" ' +
                              'data-cantidad="' + item.cantidad + '"';
              html += '  <td class="align-middle text-center">';
              html += '    <button class="btn btn-sm btn-outline-primary rounded-pill btn-solicitar-traslado" ' + dataAttrs + '>';
              html += '      <i class="fa-solid fa-truck-ramp-box me-1"></i>Solicitar';
              html += '    </button>';
              html += '  </td>';
            }
            html += '</tr>';
          });

          html += '      </tbody></table>';
          html += '  </div></div></div>';
        });

        if (globalResultsEl) {
          globalResultsEl.innerHTML = html;
          globalResultsEl.classList.remove('d-none');
        }
      })
      .catch(function(err) {
        if (globalSpinnerEl) globalSpinnerEl.classList.add('d-none');
        if (globalSearchBtnEl) globalSearchBtnEl.disabled = false;
        console.error('Error en búsqueda global:', err);
        mostrarAlertaGlobal('danger', 'Error de conexión. Intente nuevamente.');
      });
  }

  function mostrarAlertaGlobal(tipo, msg) {
    if (!globalResultsEl) return;
    globalResultsEl.innerHTML = '<div class="alert alert-' + tipo + ' border-0" style="border-radius:10px;">' +
      '<i class="fa-solid fa-triangle-exclamation me-2"></i>' + msg + '</div>';
    globalResultsEl.classList.remove('d-none');
  }

  // Enter en el input (prevenir submit del form si existiera)
  if (globalSearchInputEl) {
    globalSearchInputEl.addEventListener('keydown', function(e) {
      if (e.key === 'Enter') { 
        e.preventDefault(); 
        ejecutarBusquedaGlobal(); 
      }
    });

    // Debounce automático (400ms) al escribir
    globalSearchInputEl.addEventListener('input', function() {
      clearTimeout(globalSearchDebounce);
      var val = this.value.trim();
      
      if (val.length >= 3) {
        globalSearchDebounce = setTimeout(function() {
          ejecutarBusquedaGlobal();
        }, 400);
      } else {
        // Limpiar resultados si el texto es muy corto
        if (globalSpinnerEl)  globalSpinnerEl.classList.add('d-none');
        if (globalResultsEl) {
          globalResultsEl.classList.add('d-none');
          globalResultsEl.innerHTML = '';
        }
        if (globalEmptyEl)    globalEmptyEl.classList.remove('d-none');
      }
    });
  }

  // ── Modal de Confirmación de Traslado ──────────────────────────────────────
  var modalTrasladoEl = document.getElementById('modalSolicitudTraslado');
  var modalTraslado   = modalTrasladoEl ? new bootstrap.Modal(modalTrasladoEl) : null;

  // Abrir modal al hacer clic en "Solicitar"
  document.addEventListener('click', function(e) {
    var btn = e.target.closest('.btn-solicitar-traslado');
    if (!btn) return;

    var idStock  = btn.dataset.idstock;
    var tipo     = btn.dataset.tipo;
    var nombre   = btn.dataset.nombre;
    var detalle  = btn.dataset.detalle;
    var origen   = btn.dataset.origen;
    var cantidad = parseInt(btn.dataset.cantidad, 10);

    // Rellenar modal
    document.getElementById('trasladoIdStock').value           = idStock;
    document.getElementById('trasladoTipo').value              = tipo;
    document.getElementById('trasladoNombreProducto').textContent = nombre;
    document.getElementById('trasladoDetalle').textContent     = detalle;
    document.getElementById('trasladoOrigen').textContent      = origen;
    document.getElementById('trasladoDestino').textContent     = 'Tu sucursal / Tu almacén activo';

    // Campo cantidad: solo para repuestos
    var wrapCant = document.getElementById('wrapperCantidadTraslado');
    if (tipo === 'repuesto') {
      wrapCant.classList.remove('d-none');
      document.getElementById('trasladoCantidad').max   = cantidad;
      document.getElementById('trasladoCantidad').value = 1;
      document.getElementById('trasladoDisponible').textContent = cantidad;
    } else {
      wrapCant.classList.add('d-none');
    }

    if (modalTraslado) modalTraslado.show();
  });

  // Confirmar solicitud de traslado
  var btnConfirmar = document.getElementById('btnConfirmarTraslado');
  if (btnConfirmar) {
    btnConfirmar.addEventListener('click', function() {
      var idStock  = document.getElementById('trasladoIdStock').value;
      var tipo     = document.getElementById('trasladoTipo').value;
      var cantidad = tipo === 'repuesto'
        ? parseInt(document.getElementById('trasladoCantidad').value, 10)
        : 1;

      if (isNaN(cantidad) || cantidad < 1) {
        alert('Ingrese una cantidad válida.');
        return;
      }

      btnConfirmar.disabled = true;
      btnConfirmar.innerHTML = '<span class="spinner-border spinner-border-sm me-2"></span>Enviando...';

      var csrfToken = document.querySelector('[name=csrfmiddlewaretoken]');
      var token = csrfToken ? csrfToken.value : '';

      var fd = new FormData();
      fd.append('id_stock', idStock);
      fd.append('cantidad', cantidad);
      if (token) fd.append('csrfmiddlewaretoken', token);

      fetch('/stock/api/solicitar-traslado/', {
        method: 'POST',
        headers: { 'X-CSRFToken': getCookie('csrftoken') },
        body: fd
      })
      .then(function(resp) { return resp.json(); })
      .then(function(data) {
        btnConfirmar.disabled = false;
        btnConfirmar.innerHTML = '<i class="fa-solid fa-paper-plane me-2"></i>Confirmar Solicitud';

        if (modalTraslado) modalTraslado.hide();

        if (data.ok) {
          mostrarToastTraslado(
            'success',
            '✅ Solicitud #' + data.id_transferencia + ' creada',
            data.message
          );
        } else {
          mostrarToastTraslado('danger', '❌ Error', data.error || 'No se pudo crear la solicitud.');
        }
      })
      .catch(function(err) {
        btnConfirmar.disabled = false;
        btnConfirmar.innerHTML = '<i class="fa-solid fa-paper-plane me-2"></i>Confirmar Solicitud';
        console.error(err);
        mostrarToastTraslado('danger', '❌ Error de conexión', 'Intente nuevamente.');
      });
    });
  }

  // Toast de notificación
  function mostrarToastTraslado(tipo, titulo, cuerpo) {
    var toastContainer = document.getElementById('toastContainerGlobal');
    if (!toastContainer) {
      toastContainer = document.createElement('div');
      toastContainer.id = 'toastContainerGlobal';
      toastContainer.className = 'position-fixed top-0 end-0 p-3';
      toastContainer.style.zIndex = '9999';
      document.body.appendChild(toastContainer);
    }

    var bgColor = tipo === 'success' ? '#198754' : '#dc3545';
    var id = 'toast_' + Date.now();
    var toastHtml = '<div id="' + id + '" class="toast align-items-center text-white border-0 mb-2 show" ' +
      'role="alert" style="background:' + bgColor + '; border-radius: 12px; min-width: 300px; max-width: 420px;">' +
      '  <div class="d-flex">' +
      '    <div class="toast-body">' +
      '      <strong class="d-block mb-1">' + titulo + '</strong>' +
      '      <span style="font-size: 0.87rem;">' + cuerpo + '</span>' +
      '    </div>' +
      '    <button type="button" class="btn-close btn-close-white me-2 m-auto" ' +
      '      onclick="this.closest(\'.toast\').remove()"></button>' +
      '  </div>' +
      '</div>';

    toastContainer.insertAdjacentHTML('beforeend', toastHtml);
    setTimeout(function() {
      var el = document.getElementById(id);
      if (el) el.remove();
    }, 6000);
  }

  // Validación en tiempo real para precios de venta vs precio de compra
  const inputsPrecioVenta = document.querySelectorAll('.validation-precio-venta');
  inputsPrecioVenta.forEach(input => {
    input.addEventListener('change', function() {
      const form = this.closest('form');
      if (form) {
        const inputCompra = form.querySelector('.validation-precio-compra');
        if (inputCompra) {
          const precioCompra = parseFloat(inputCompra.value) || 0;
          const precioVenta = parseFloat(this.value) || 0;
          
          if (precioVenta > 0 && precioVenta < precioCompra) {
            Swal.fire({
              title: 'Error',
              text: 'El precio no puede ser menor al Precio de Compra (S/ ' + precioCompra.toFixed(2) + ').',
              icon: 'warning',
              confirmButtonText: 'Entendido'
            });
            this.value = '0.00';
          }
        }
      }
    });
  });
  
  const inputsPrecioCompra = document.querySelectorAll('.validation-precio-compra');
  inputsPrecioCompra.forEach(input => {
    input.addEventListener('change', function() {
      const form = this.closest('form');
      if (form) {
        const precioCompra = parseFloat(this.value) || 0;
        const ventas = form.querySelectorAll('.validation-precio-venta');
        ventas.forEach(venta => {
          const precioVenta = parseFloat(venta.value) || 0;
          if (precioVenta > 0 && precioVenta < precioCompra) {
             venta.value = '0.00';
          }
        });
      }
    });
  });

  // Helper: leer cookie CSRF
  function getCookie(name) {
    var v = document.cookie.match('(^|;) ?' + name + '=([^;]*)(;|$)');
    return v ? v[2] : '';
  }

});

// ══ HISTORIAL DE RECAUDACIÓN POR VEHÍCULO ══════════════════════════════════
// Pestaña 3 - Buscar vehículos para historial

var historialDebounce = null;
var currentHistorialQuery = '';
var currentHistorialPage = 1;

// Escuchar cuando se abre la pestaña para cargar la lista inicial
document.addEventListener('DOMContentLoaded', function() {
  var tabHistorial = document.getElementById('tab-historial-btn');
  if (tabHistorial) {
    tabHistorial.addEventListener('shown.bs.tab', function (e) {
      // Si está vacío, cargar la página 1 inicial
      if (document.getElementById('historialSearchResults').innerHTML.trim() === '') {
        _ejecutarBusquedaHistorial('', 1);
      }
    });
  }
});

function buscarVehiculosHistorial(valor, page) {
  clearTimeout(historialDebounce);
  historialDebounce = setTimeout(function() {
    _ejecutarBusquedaHistorial(valor, page || 1);
  }, 350);
}

function cambiarPaginaHistorial(page) {
    _ejecutarBusquedaHistorial(currentHistorialQuery, page);
}

function _ejecutarBusquedaHistorial(query, page) {
  currentHistorialQuery = (query === undefined || query === null) ? '' : query.trim();
  currentHistorialPage = page || 1;
  
  var spinner  = document.getElementById('historialSearchSpinner');
  var empty    = document.getElementById('historialSearchEmpty');
  var results  = document.getElementById('historialSearchResults');

  spinner.classList.remove('d-none');
  empty.classList.add('d-none');
  results.classList.add('d-none');

  var url = '/stock/api/historial/buscar/?page=' + currentHistorialPage;
  if (currentHistorialQuery) {
      url += '&q=' + encodeURIComponent(currentHistorialQuery);
  }

  fetch(url)
    .then(function(resp) { return resp.json(); })
    .then(function(data) {
      spinner.classList.add('d-none');

      if (!data.vehiculos || data.vehiculos.length === 0) {
        results.classList.add('d-none');
        empty.classList.remove('d-none');
        empty.innerHTML =
          '<div style="font-size:4rem;opacity:0.25;margin-bottom:1rem;color:#ffd200;"><i class="fa-solid fa-motorcycle"></i></div>' +
          '<p style="color:rgba(255,255,255,0.5);" class="fs-6">No se encontraron vehículos.</p>';
        return;
      }

      empty.classList.add('d-none');
      results.classList.remove('d-none');

      var html = '<div class="d-flex justify-content-between align-items-center mb-3">';
      html += '<p style="color:rgba(255,255,255,0.5);" class="mb-0 small"><i class="fa-solid fa-check-circle text-warning me-1"></i>Mostrando ' + data.vehiculos.length + ' de ' + data.total + ' vehículo(s)</p>';
      html += '</div>';
      
      html += '<div class="row g-3 mb-4">';

      data.vehiculos.forEach(function(v) {
        // Badge de estado
        var enStockBadge = v.en_stock
          ? '<span class="badge bg-success ms-1">En Stock</span>'
          : '<span class="badge bg-secondary ms-1">Sin Stock</span>';
          
        var vendidoBadge = '';
        if (v.fue_vendido) {
            var tipoText = v.tipo_venta ? ' (' + v.tipo_venta + ')' : '';
            vendidoBadge = '<span class="badge ms-1" style="background:#3b82f6;">Vendido' + tipoText + '</span>';
        }

        html +=
          '<div class="col-md-6 col-xl-4">' +
          '<div class="card border-0 h-100" style="background:rgba(255,255,255,0.07);border-radius:14px;border:1px solid rgba(255,210,0,0.15)!important;transition:transform 0.15s;" ' +
          'onmouseover="this.style.transform=\'translateY(-3px)\'" onmouseout="this.style.transform=\'\'"> ' +
          '<div class="card-body d-flex flex-column gap-2">' +
          '<div class="fw-bold" style="color:#ffd200;font-size:0.95rem;">' + v.nombre + '</div>' +
          '<div class="d-flex flex-wrap gap-1">' + enStockBadge + vendidoBadge + '</div>' +
          '<div class="small" style="color:rgba(255,255,255,0.6);">' +
            '<i class="fa-solid fa-gear me-1 text-warning opacity-75"></i>Motor: <code style="color:#7dd3fc; background:transparent!important; padding:0;">' + v.serie_motor + '</code>' +
          '</div>' +
          '<div class="small" style="color:rgba(255,255,255,0.6);">' +
            '<i class="fa-solid fa-car me-1 text-warning opacity-75"></i>Chasis: <code style="color:#7dd3fc; background:transparent!important; padding:0;">' + v.serie_chasis + '</code>' +
          '</div>' +
          '<div class="small" style="color:rgba(255,255,255,0.6);">' +
            '<i class="fa-solid fa-calendar me-1 text-warning opacity-75"></i>Año: ' + v.anio + ' &nbsp;|&nbsp; ' +
            '<i class="fa-solid fa-circle-info me-1 text-warning opacity-75"></i>' + v.estado_producto +
          '</div>' +
          '<div class="mt-auto pt-2">' +
            '<button class="btn btn-sm fw-bold w-100" ' +
              'onclick="abrirModalRecaudacion(' + v.id_vehiculo + ')" ' +
              'style="background:linear-gradient(135deg,#f7971e,#ffd200);color:#000;border:none;border-radius:10px;">' +
              '<i class="fa-solid fa-coins me-2"></i>Ver Recaudación' +
            '</button>' +
          '</div>' +
          '</div></div></div>';
      });
      html += '</div>';

      // Añadir paginación si hay más de 1 página
      if (data.total_pages > 1) {
        var onClickFnStr = 'cambiarPaginaHistorial(__PAGE__)';
        // GenerarHTMLPaginacion asume un entorno Bootstrap con ciertas clases, pero como estamos en un contenedor dark,
        // envolveremos en un div para aislarlo o usaremos el HTML paginador existente.
        html += '<div class="d-flex justify-content-center bg-white rounded-3 p-2 d-inline-block mx-auto mb-3" style="width:fit-content;">' + 
                 generarHtmlPaginacion(data.page, data.total_pages, onClickFnStr) + 
                '</div>';
      }

      results.innerHTML = html;
    })
    .catch(function(err) {
      spinner.classList.add('d-none');
      empty.classList.remove('d-none');
      empty.innerHTML = '<i class="fa-solid fa-triangle-exclamation fa-2x text-danger mb-2"></i><br><span style="color:rgba(255,255,255,0.5);">Error al buscar. Intente de nuevo.</span>';
      console.error('Error en buscarVehiculosHistorial:', err);
    });
}

function abrirModalRecaudacion(idVehiculo) {
  // Reset estado del modal
  document.getElementById('recaudacion-loading').style.display = 'block';
  document.getElementById('recaudacion-content').style.display = 'none';
  document.getElementById('recaudacion-error').style.display = 'none';
  document.getElementById('recaudacion-vehiculo-nombre').textContent = 'Cargando...';

  var modalEl = document.getElementById('modalRecaudacion');
  _mostrarModalRecaudacion(idVehiculo, modalEl);
}

function _mostrarModalRecaudacion(idVehiculo, modalEl) {
  // Destruir cualquier instancia anterior para evitar el bug del backdrop duplicado
  var instanciaAnterior = bootstrap.Modal.getInstance(modalEl);
  if (instanciaAnterior) {
    instanciaAnterior.dispose();
  }
  
  // Limpiar clases residuales de Bootstrap que bloquean la reapertura
  modalEl.classList.remove('show');
  document.body.classList.remove('modal-open');
  var backdrops = document.querySelectorAll('.modal-backdrop');
  backdrops.forEach(function(bd) { bd.remove(); });
  
  // Crear instancia nueva y mostrarla
  var modal = new bootstrap.Modal(modalEl);
  modal.show();

  // Fetch API de recaudación
  fetch('/stock/api/recaudacion/' + idVehiculo + '/')
    .then(function(resp) {
      if (!resp.ok) throw new Error('Error ' + resp.status);
      return resp.json();
    })
    .then(function(data) {
      var v = data.vehiculo;
      document.getElementById('recaudacion-vehiculo-nombre').textContent = v.nombre;

      // Ficha del vehículo
      document.getElementById('recaudacion-vehiculo-info').innerHTML =
        '<div class="col-md-3">' +
          '<div class="p-3 rounded-3" style="background:rgba(255,255,255,0.08);">' +
          '<div class="text-white-50 small">Motor</div><div class="fw-bold">' + v.serie_motor + '</div>' +
          '</div></div>' +
        '<div class="col-md-3">' +
          '<div class="p-3 rounded-3" style="background:rgba(255,255,255,0.08);">' +
          '<div class="text-white-50 small">Chasis</div><div class="fw-bold">' + v.serie_chasis + '</div>' +
          '</div></div>' +
        '<div class="col-md-3">' +
          '<div class="p-3 rounded-3" style="background:rgba(255,255,255,0.08);">' +
          '<div class="text-white-50 small">Año</div><div class="fw-bold">' + v.anio + '</div>' +
          '</div></div>' +
        '<div class="col-md-3">' +
          '<div class="p-3 rounded-3" style="background:rgba(255,255,255,0.08);">' +
          '<div class="text-white-50 small">Estado</div><div class="fw-bold">' + v.estado + '</div>' +
          '</div></div>';

      // Total
      document.getElementById('recaudacion-total').textContent = 'S/ ' + parseFloat(data.total_recaudado).toFixed(2);
      document.getElementById('recaudacion-total-ventas').textContent = data.total_ventas + ' venta(s) registrada(s)';

      // Tabla
      var filas = '';
      data.ventas.forEach(function(venta, idx) {
        var tipoBadge = venta.tipo === 'Crédito'
          ? '<span class="badge rounded-pill" style="background:#3b82f6;">Crédito</span>'
          : '<span class="badge rounded-pill bg-success">Contado</span>';

        var estadoBadge = '-';
        if (venta.estado_credito) {
          var ec = venta.estado_credito.toLowerCase();
          if (ec === 'mora') estadoBadge = '<span class="badge bg-danger">' + venta.estado_credito + '</span>';
          else if (ec === 'pagado') estadoBadge = '<span class="badge bg-success">' + venta.estado_credito + '</span>';
          else if (ec === 'cancelado') estadoBadge = '<span class="badge bg-warning text-dark">' + venta.estado_credito + '</span>';
          else if (ec === 'anulado') estadoBadge = '<span class="badge bg-secondary">' + venta.estado_credito + '</span>';
          else estadoBadge = '<span class="badge" style="background:rgba(255,255,255,0.2);">' + venta.estado_credito + '</span>';
        }

        filas +=
          '<tr style="border-bottom: 1px solid rgba(255,255,255,0.08);">' +
          '<td class="ps-4 text-white-50">' + (idx + 1) + '</td>' +
          '<td>' + venta.fecha_venta + '</td>' +
          '<td><code style="color:#7dd3fc;">' + venta.comprobante + '</code></td>' +
          '<td>' + venta.cliente + '</td>' +
          '<td class="text-center">' + tipoBadge + '</td>' +
          '<td class="text-center">' + estadoBadge + '</td>' +
          '<td class="text-end text-white-50">S/ ' + parseFloat(venta.inicial).toFixed(2) + '</td>' +
          '<td class="text-end text-white-50">S/ ' + parseFloat(venta.cuotas_pagadas).toFixed(2) + '</td>' +
          '<td class="text-end pe-4 fw-bold" style="color:#ffd200;">S/ ' + parseFloat(venta.recaudado).toFixed(2) + '</td>' +
          '</tr>';
      });

      document.getElementById('recaudacion-tabla-body').innerHTML = filas ||
        '<tr><td colspan="9" class="text-center text-white-50 py-4">Este vehículo aún no tiene ventas registradas.</td></tr>';

      document.getElementById('recaudacion-tabla-foot').innerHTML =
        '<tr><td colspan="8" class="text-end pe-3">TOTAL RECAUDADO:</td>' +
        '<td class="text-end pe-4" style="font-size:1.1rem;">S/ ' + parseFloat(data.total_recaudado).toFixed(2) + '</td></tr>';

      document.getElementById('recaudacion-loading').style.display = 'none';
      document.getElementById('recaudacion-content').style.display = 'block';
    })
    .catch(function(err) {
      document.getElementById('recaudacion-loading').style.display = 'none';
      document.getElementById('recaudacion-error').style.display = 'block';
      console.error('Error al cargar recaudacion:', err);
    });
}


