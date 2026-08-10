
// ==========================================
// SUGERENCIAS INTELIGENTES DE COMPRA
// Fuente: API /stock/api/repuestos/ (todas las páginas)
// La variable de template 'repuestos_stock' ya no se usa porque
// el módulo es Server-Side Processing (AJAX). Leemos la API directamente.
// ==========================================

// Cache en memoria para no repetir la carga si ya se consultó
let _inventarioRepuestosCache = null;

async function _cargarInventarioCompleto() {
  if (_inventarioRepuestosCache !== null) return _inventarioRepuestosCache;

  let todos = [];
  let pagina = 1;
  let totalPaginas = 1;

  do {
    try {
      const resp = await fetch('/stock/api/repuestos/?page=' + pagina + '&page_size=500');
      const data = await resp.json();
      if (data.grupos && data.grupos.length > 0) {
        todos = todos.concat(data.grupos);
      }
      totalPaginas = data.total_paginas || 1;
      pagina++;
    } catch(e) {
      console.error('Error cargando inventario para sugerencias:', e);
      break;
    }
  } while (pagina <= totalPaginas);

  _inventarioRepuestosCache = todos;
  return todos;
}

async function abrirSugerenciasCompra() {
  // Mostrar modal con spinner mientras carga
  var modalEl = document.getElementById('modalSugerencias');
  document.body.appendChild(modalEl);
  var modal = new bootstrap.Modal(modalEl);

  const tbody = $('#tablaSugerencias tbody');
  tbody.empty();
  tbody.html('<tr><td colspan="4" class="text-center py-3"><span class="spinner-border spinner-border-sm me-2"></span>Analizando inventario...</td></tr>');
  $('#tablaSugerencias').removeClass('d-none');
  $('#noSugerenciasMsg').addClass('d-none');
  modal.show();

  const inventario = await _cargarInventarioCompleto();

  tbody.empty();
  let itemsCriticos = 0;

  inventario.forEach(item => {
    // Crítico: cantidad_total <= stock_minimo
    const esCritico = item.estado_salud === 'critico' || item.cantidad_total <= item.stock_minimo;
    if (esCritico) {
      // Sugerir hasta alcanzar stock_maximo; si no tiene máximo, sugerir hasta stock_minimo * 2
      const objetivo = item.stock_maximo > 0 ? item.stock_maximo : item.stock_minimo * 2;
      const aPedir = Math.max(0, objetivo - item.cantidad_total);
      if (aPedir > 0) {
        itemsCriticos++;
        const estadoBadge = item.cantidad_total === 0
          ? '<span class="badge bg-dark rounded-pill fs-6">0</span>'
          : '<span class="badge bg-danger rounded-pill fs-6 pulse-animation">' + item.cantidad_total + '</span>';
        tbody.append(
          '<tr>' +
          '<td class="fw-bold text-dark"><i class="fa-solid fa-tag text-danger me-2"></i>' + item.nombre + '</td>' +
          '<td class="text-center">' + estadoBadge + '</td>' +
          '<td class="text-center text-muted">' + item.stock_minimo + '</td>' +
          '<td class="text-center"><span class="badge bg-success rounded-pill fs-6">+' + aPedir + '</span></td>' +
          '</tr>'
        );
      }
    }
  });

  if (itemsCriticos > 0) {
    $('#tablaSugerencias').removeClass('d-none');
    $('#noSugerenciasMsg').addClass('d-none');
  } else {
    $('#tablaSugerencias').addClass('d-none');
    $('#noSugerenciasMsg').removeClass('d-none');
  }
}

async function exportarSugerenciasExcel() {
  const inventario = await _cargarInventarioCompleto();
  let hayDatos = false;

  let tablaHTML = `
    <html xmlns:x="urn:schemas-microsoft-com:office:excel">
    <head>
      <meta charset="utf-8">
      <style>
        table { border-collapse: collapse; font-family: Arial, sans-serif; }
        th { background-color: #6f42c1; color: white; font-weight: bold; border: 1px solid #000; padding: 10px; text-align: center; }
        td { border: 1px solid #ddd; padding: 8px; text-align: center; }
        .text-left { text-align: left; }
      </style>
    </head>
    <body>
      <h3>Sugerencias de Compra de Repuestos</h3>
      <table>
        <thead>
          <tr>
            <th>Repuesto</th>
            <th>Stock Actual</th>
            <th>Stock Mínimo</th>
            <th>Cantidad Sugerida a Pedir</th>
          </tr>
        </thead>
        <tbody>
  `;

  inventario.forEach(item => {
    const esCritico = item.estado_salud === 'critico' || item.cantidad_total <= item.stock_minimo;
    if (esCritico) {
      const objetivo = item.stock_maximo > 0 ? item.stock_maximo : item.stock_minimo * 2;
      const aPedir = Math.max(0, objetivo - item.cantidad_total);
      if (aPedir > 0) {
        hayDatos = true;
        tablaHTML += `
          <tr>
            <td class="text-left">${item.nombre}</td>
            <td style="color: #dc3545; font-weight: bold;">${item.cantidad_total}</td>
            <td>${item.stock_minimo}</td>
            <td style="color: #198754; font-weight: bold;">+${aPedir}</td>
          </tr>
        `;
      }
    }
  });

  tablaHTML += `
        </tbody>
      </table>
    </body>
    </html>
  `;

  if (!hayDatos) {
    Swal.fire('Información', 'No hay datos críticos para exportar.', 'info');
    return;
  }

  const uri = 'data:application/vnd.ms-excel;base64,';
  const base64data = btoa(unescape(encodeURIComponent(tablaHTML)));
  const link = document.createElement('a');
  link.href = uri + base64data;
  link.download = 'Sugerencias_Compras.xls';
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
}

