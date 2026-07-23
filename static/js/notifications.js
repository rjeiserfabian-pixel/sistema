/**
 * notifications.js - Gestión de notificaciones de cuotas vencidas
 *
 * COMPORTAMIENTO:
 *  - Sesión nueva (login):
 *    → GET #1 al cargar cualquier módulo: consulta + intenta sonar
 *    → Espera 60 segundos
 *    → GET #2: consulta + intenta sonar
 *    → Ya no hace nada más hasta cerrar sesión
 *  - Logout: resetea el contador para la siguiente sesión
 *
 * El sonido se intenta en cuanto llega la respuesta del GET.
 * Si el navegador lo bloquea (autoplay), se reproduce en el primer
 * clic/tecla que haga el usuario en esa página.
 */

document.addEventListener('DOMContentLoaded', function () {

    // ── Elementos del DOM ─────────────────────────────────────────
    const badge           = document.getElementById('notification-badge');
    const countDisplay    = document.getElementById('notification-count');
    const itemsContainer  = document.getElementById('notification-items');
    const soundToggle     = document.getElementById('toggle-sound');
    const audio           = document.getElementById('notification-sound');
    const uploadContainer = document.getElementById('upload-sound-container');
    const btnUpload       = document.getElementById('btn-upload-sound');
    const inputUpload     = document.getElementById('input-upload-sound');
    const uploadStatus    = document.getElementById('upload-status');

    // ── sessionStorage keys ───────────────────────────────────────
    const KEY_COUNT = 'notif_count';   // Cuántos GETs/sonidos se han ejecutado (0,1,2)
    const KEY_TS    = 'notif_ts';      // Timestamp del GET #1 (para calcular los 60s)
    const MAX       = 2;               // Máximo de sonidos por sesión
    const INTERVALO = 60_000;          // 60 segundos

    function getCount()   { return parseInt(sessionStorage.getItem(KEY_COUNT) || '0', 10); }
    function getTs()      { return parseInt(sessionStorage.getItem(KEY_TS)    || '0', 10); }
    function setCount(n)  { sessionStorage.setItem(KEY_COUNT, String(n)); }
    function resetAll()   { sessionStorage.removeItem(KEY_COUNT); sessionStorage.removeItem(KEY_TS); }

    // Limpiar al logout
    const logoutBtn = document.getElementById('logout-link');
    if (logoutBtn) logoutBtn.addEventListener('click', resetAll);

    // ── Audio: desbloqueo ─────────────────────────────────────────
    let audioReady   = false;   // El navegador permite reproducir
    let pendingSound = false;   // Hay un sonido esperando a que el usuario interactúe

    function tryPlay() {
        if (!audio || !audio.src) return;
        audio.currentTime = 0;
        audio.play()
            .then(() => { audioReady = true; pendingSound = false; })
            .catch(() => {
                // Navegador bloqueó autoplay → esperar primera interacción
                pendingSound = true;
            });
    }

    function onUserInteraction() {
        audioReady = true;
        if (pendingSound) {
            pendingSound = false;
            tryPlay();
        }
    }

    ['click', 'keydown', 'touchstart', 'pointerdown'].forEach(evt =>
        document.addEventListener(evt, onUserInteraction, { passive: true })
    );

    function setAudioSrc(url) {
        if (!audio || !url) return;
        const rel = audio.src.replace(window.location.origin, '');
        if (rel !== url) { audio.src = url; audio.load(); }
    }

    // ── Fetch de notificaciones ───────────────────────────────────
    function fetchNotifications(withSound) {
        fetch('/api/notificaciones/vencidas/')
            .then(r => r.json())
            .then(data => {
                if (!data.ok) return;

                const count = data.count;

                // Badge
                badge.textContent = count;
                badge.classList.toggle('d-none', count === 0);
                countDisplay.textContent = count;

                // Lista
                renderNotifications(data.notificaciones);

                // Toggle / src audio
                if (soundToggle) {
                    soundToggle.checked = data.sonido_activo;
                    toggleUpload(data.sonido_activo);
                }
                if (data.sonido_url) setAudioSrc(data.sonido_url);

                // Sonido
                if (withSound && data.sonido_activo && count > 0) {
                    tryPlay();
                }
            })
            .catch(err => console.error('Notificaciones error:', err));
    }

    // ── Render ────────────────────────────────────────────────────
    function renderNotifications(list) {
        if (!list || !list.length) {
            itemsContainer.innerHTML = `
                <li class="notification-item p-3 text-center">
                    <p class="text-muted mb-0">No tienes cuotas vencidas</p>
                </li>`;
            return;
        }
        itemsContainer.innerHTML = list.map(item => `
            <li class="notification-item p-2">
                <a href="${item.url}" class="text-decoration-none">
                    <div class="d-flex align-items-center">
                        <i class="bi bi-exclamation-circle text-danger me-2 fs-5"></i>
                        <div>
                            <h4 class="mb-0 fs-6 text-dark">${item.cliente}</h4>
                            <p class="mb-0 text-muted small">Cuota ${item.numero_cuota}: S/ ${item.monto.toFixed(2)}</p>
                            <p class="mb-0 text-danger small">Venció: ${item.fecha_vencimiento}</p>
                        </div>
                    </div>
                </a>
            </li>
            <li><hr class="dropdown-divider"></li>
        `).join('');
    }

    // ── Toggle upload ─────────────────────────────────────────────
    function toggleUpload(active) {
        if (uploadContainer) uploadContainer.classList.toggle('d-none', !active);
    }

    // ── Subir sonido ──────────────────────────────────────────────
    if (btnUpload)   btnUpload.addEventListener('click', () => inputUpload?.click());
    if (inputUpload) inputUpload.addEventListener('change', function () {
        if (!this.files?.[0]) return;
        const fd = new FormData();
        fd.append('sonido', this.files[0]);
        uploadStatus.innerHTML = '<span class="spinner-border spinner-border-sm text-primary"></span> Subiendo...';
        fetch('/api/notificaciones/subir-sonido/', {
            method: 'POST', body: fd,
            headers: { 'X-CSRFToken': getCookie('csrftoken') }
        })
        .then(r => r.json())
        .then(d => {
            if (d.ok) {
                uploadStatus.innerHTML = '<span class="text-success"><i class="bi bi-check-circle"></i> ¡Listo!</span>';
                setAudioSrc(d.url);
                tryPlay();
                setTimeout(() => uploadStatus.innerHTML = '', 4000);
            } else {
                uploadStatus.innerHTML = `<span class="text-danger">${d.error}</span>`;
            }
        })
        .catch(() => uploadStatus.innerHTML = '<span class="text-danger">Error al subir</span>');
    });

    // ── Toggle preferencia sonido ─────────────────────────────────
    if (soundToggle) soundToggle.addEventListener('change', function () {
        toggleUpload(this.checked);
        const fd = new FormData();
        fd.append('activo', this.checked);
        fetch('/api/notificaciones/config-sonido/', {
            method: 'POST', body: fd,
            headers: { 'X-CSRFToken': getCookie('csrftoken') }
        }).catch(() => {});
    });

    // ── CSRF ──────────────────────────────────────────────────────
    function getCookie(name) {
        const c = document.cookie.split(';')
            .map(s => s.trim())
            .find(s => s.startsWith(name + '='));
        return c ? decodeURIComponent(c.split('=')[1]) : null;
    }

    // ════════════════════════════════════════════════════════════
    // LÓGICA PRINCIPAL
    //
    //  count = 0  → Primera página post-login
    //               → GET + sonido #1
    //               → Guardar timestamp
    //               → Programar GET + sonido #2 en 60s
    //               → setCount(1)
    //
    //  count = 1  → Ya sonó #1 en página anterior
    //               → Calcular tiempo restante hasta los 60s
    //               → Si ya pasaron: GET + sonido #2 ahora
    //               → Si no: setTimeout con el tiempo restante
    //               → setCount(2) cuando ejecute el #2
    //
    //  count >= 2 → Límite alcanzado: no hacer nada
    // ════════════════════════════════════════════════════════════
    const count = getCount();

    if (count === 0) {
        // ── SONIDO #1 ─────────────────────────────────────────────
        console.log('🔔 Notificaciones: sonido #1');
        fetchNotifications(true);               // CON sonido
        sessionStorage.setItem(KEY_TS, String(Date.now()));
        setCount(1);

        // Programar sonido #2 en 60s desde esta misma página
        setTimeout(() => {
            if (getCount() < MAX) {
                console.log('🔔 Notificaciones: sonido #2 (60s)');
                fetchNotifications(true);       // CON sonido
                setCount(2);
            }
        }, INTERVALO);

    } else if (count === 1) {
        // ── Página nueva antes de que se cumplan los 60s ──────────
        const elapsed   = Date.now() - getTs();
        const remaining = INTERVALO - elapsed;

        if (remaining <= 0) {
            // Los 60s ya pasaron mientras navegaba → sonar ahora
            console.log('🔔 Notificaciones: sonido #2 (diferido por navegación)');
            fetchNotifications(true);
            setCount(2);
        } else {
            // Esperar el tiempo que queda
            console.log(`🔔 Notificaciones: sonido #2 en ${Math.round(remaining / 1000)}s`);
            setTimeout(() => {
                if (getCount() < MAX) {
                    console.log('🔔 Notificaciones: sonido #2 (temporizador)');
                    fetchNotifications(true);
                    setCount(2);
                }
            }, remaining);
        }

    } else {
        // ── Límite alcanzado ─────────────────────────────────────
        console.log('🛑 Notificaciones: límite de 2 sonidos alcanzado.');
    }

});
