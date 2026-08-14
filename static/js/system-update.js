(() => {
    'use strict';

    const POLL_INTERVAL = 3000;
    let pollTimer = null;
    let lastState = null;

    function ensureOverlay() {
        let overlay = document.getElementById('system-update-overlay');
        if (overlay) return overlay;

        overlay = document.createElement('div');
        overlay.id = 'system-update-overlay';
        overlay.className = 'system-update-overlay d-none';
        overlay.setAttribute('aria-live', 'polite');
        overlay.innerHTML = `
            <div class="system-update-dialog" role="dialog" aria-modal="true" aria-labelledby="system-update-title">
                <div class="system-update-icon"><i class="bi bi-arrow-repeat"></i></div>
                <h2 id="system-update-title">Atualização do sistema</h2>
                <p id="system-update-message">Aguarde enquanto o sistema é atualizado.</p>
                <div class="system-update-progress" aria-hidden="true">
                    <div id="system-update-progress-bar" class="system-update-progress-bar" style="width:0%"></div>
                </div>
                <div id="system-update-progress-label" class="system-update-progress-label">0%</div>
                <div id="system-update-error" class="system-update-error d-none"></div>
            </div>`;
        document.body.appendChild(overlay);
        return overlay;
    }

    function setBusy(isBusy) {
        document.documentElement.classList.toggle('system-update-active', isBusy);
        document.querySelectorAll('button, a.btn, input[type="submit"], input[type="button"]').forEach((element) => {
            if (element.closest('#system-update-overlay')) return;
            if (isBusy) {
                if (!element.dataset.updateDisabled) {
                    element.dataset.updateDisabled = element.disabled ? 'true' : 'false';
                }
                element.disabled = true;
                element.setAttribute('aria-disabled', 'true');
            } else if (element.dataset.updateDisabled) {
                element.disabled = element.dataset.updateDisabled === 'true';
                element.removeAttribute('aria-disabled');
                delete element.dataset.updateDisabled;
            }
        });
    }

    function render(state) {
        const overlay = ensureOverlay();
        const active = !['idle', 'ready'].includes(state.state);
        const failed = state.state === 'failed';
        const ready = state.state === 'ready';
        const message = document.getElementById('system-update-message');
        const progress = document.getElementById('system-update-progress-bar');
        const label = document.getElementById('system-update-progress-label');
        const error = document.getElementById('system-update-error');

        if (state.version_to) {
            document.getElementById('system-update-title').textContent = `Atualização para ${state.version_to}`;
        }
        message.textContent = state.message || 'Atualização em andamento.';
        progress.style.width = `${Math.max(0, Math.min(100, Number(state.progress || 0)))}%`;
        label.textContent = `${Math.max(0, Math.min(100, Number(state.progress || 0)))}%`;
        error.textContent = state.error || '';
        error.classList.toggle('d-none', !failed);
        overlay.classList.toggle('d-none', !active && !failed && !ready);
        setBusy(active);

        if (ready && state.reload_required && lastState && lastState.state !== 'ready') {
            setTimeout(() => window.location.reload(), 1200);
        }
        lastState = state;
    }

    async function poll() {
        try {
            const response = await fetch('/api/system/update/status', {
                headers: { 'X-Requested-With': 'XMLHttpRequest' },
                cache: 'no-store'
            });
            if (response.ok) render(await response.json());
        } catch (_) {
            // O sistema pode estar reiniciando; a próxima consulta tentará novamente.
        }
        pollTimer = setTimeout(poll, POLL_INTERVAL);
    }

    document.addEventListener('DOMContentLoaded', () => {
        ensureOverlay();
        poll();
    });
})();
