(() => {
    'use strict';

    const POLL_INTERVAL = 3000;

    // Estados que bloqueiam a interface por completo (pointer-events: none).
    // ready_to_restart NÃO está nessa lista: o overlay de recuperação é exibido,
    // mas os formulários e controles da página continuam acessíveis.
    const BLOCKING_STATES = new Set([
        'maintenance_pending',
        'preparing',
        'backing_up',
        'downloading',
        'validating',
        'migrating',
        'switching',
        'restarting',
        'verifying',
        'blocked',
    ]);

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
                <div id="system-update-recovery" class="system-update-recovery d-none">
                    <p class="system-update-recovery-hint">
                        A atualização foi preparada mas o reinício automático não está configurado.<br>
                        Se o serviço já está em execução na versão correta, você pode limpar este estado.
                    </p>
                    <button id="system-update-clear-btn" class="btn btn-sm btn-outline-secondary mt-2">
                        <i class="bi bi-x-circle me-1"></i>Limpar estado e continuar
                    </button>
                </div>
            </div>`;
        document.body.appendChild(overlay);

        overlay.querySelector('#system-update-clear-btn').addEventListener('click', handleClearRestart);
        return overlay;
    }

    function setCsrfHeader(headers) {
        const meta = document.querySelector('meta[name="csrf-token"]');
        if (meta) headers['X-CSRFToken'] = meta.getAttribute('content');
        return headers;
    }

    async function handleClearRestart() {
        const btn = document.getElementById('system-update-clear-btn');
        if (!btn) return;
        btn.disabled = true;
        btn.innerHTML = '<span class="spinner-border spinner-border-sm me-1"></span>Aguarde...';
        try {
            const response = await fetch('/api/system/update/clear-restart', {
                method: 'POST',
                headers: setCsrfHeader({ 'X-Requested-With': 'XMLHttpRequest' }),
                cache: 'no-store',
            });
            const data = await response.json();
            if (response.ok && data.success) {
                // Força um novo poll imediato para atualizar a UI.
                clearTimeout(pollTimer);
                poll();
            } else {
                btn.disabled = false;
                btn.innerHTML = '<i class="bi bi-x-circle me-1"></i>Limpar estado e continuar';
                alert(data.message || 'Não foi possível limpar o estado. Tente novamente.');
            }
        } catch (_) {
            btn.disabled = false;
            btn.innerHTML = '<i class="bi bi-x-circle me-1"></i>Limpar estado e continuar';
        }
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
        const isBusy = BLOCKING_STATES.has(state.state);
        const failed = state.state === 'failed';
        const ready = state.state === 'ready';
        const readyToRestart = state.state === 'ready_to_restart';

        const message = document.getElementById('system-update-message');
        const progress = document.getElementById('system-update-progress-bar');
        const label = document.getElementById('system-update-progress-label');
        const error = document.getElementById('system-update-error');
        const recovery = document.getElementById('system-update-recovery');
        const clearBtn = document.getElementById('system-update-clear-btn');

        if (state.version_to) {
            document.getElementById('system-update-title').textContent = `Atualização para ${state.version_to}`;
        }

        message.textContent = readyToRestart
            ? 'Reinício manual necessário.'
            : (state.message || 'Atualização em andamento.');

        const pct = Math.max(0, Math.min(100, Number(state.progress || 0)));
        progress.style.width = `${pct}%`;
        label.textContent = `${pct}%`;
        error.textContent = state.error || '';
        error.classList.toggle('d-none', !failed);

        // Painel de recuperação: visível somente em ready_to_restart.
        if (recovery) {
            recovery.classList.toggle('d-none', !readyToRestart);
            if (clearBtn) {
                clearBtn.disabled = false;
                clearBtn.innerHTML = '<i class="bi bi-x-circle me-1"></i>Limpar estado e continuar';
            }
        }

        // Overlay visível durante qualquer estado não-idle (exceto idle puro).
        const showOverlay = isBusy || failed || ready || readyToRestart;
        overlay.classList.toggle('d-none', !showOverlay);

        // Bloqueio global de ponteiro APENAS para estados verdadeiramente bloqueantes.
        setBusy(isBusy);

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
