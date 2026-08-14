// registrofacil/static/js/processos/record_locking.js

import { showToast } from '../utils/dom_helpers.js';

/**
 * Inicializa a lógica de bloqueio de edição para um registro.
 * Esta função é ativada apenas nas páginas de edição de processo.
 * @param {object} FlaskRoutes - Objeto contendo as rotas Flask expostas globalmente.
 * @param {number} LOCK_TIMEOUT_MINUTES_JS - Tempo de timeout do lock em minutos, vindo do backend.
 */
export function initializeRecordLocking(FlaskRoutes, LOCK_TIMEOUT_MINUTES_JS) {
    // Obtém o ID do processo do campo oculto no formulário (se existir).
    const currentProcessIdInput = document.querySelector('#form-processo input[name="id"]');
    const currentProcessId = currentProcessIdInput ? parseInt(currentProcessIdInput.value) : null;

    // A lógica de bloqueio só é ativada se estamos numa página de edição de processo E há um ID de processo.
    if (!currentProcessId || typeof FlaskRoutes === 'undefined' || !window.location.pathname.startsWith(FlaskRoutes.processosEditarBase.replace('/_ID_',''))) {
        console.log("initializeRecordLocking: Não é uma tela de edição de processo ou ID não encontrado. Lógica de bloqueio não será ativada.");
        return;
    }
    console.log("initializeRecordLocking: Lógica de bloqueio de edição ativada para processo.");

    // O intervalo de renovação é metade do tempo de timeout do lock para garantir que seja renovado a tempo.
    const renewInterval = (LOCK_TIMEOUT_MINUTES_JS * 60 / 2) * 1000; // Converte para milissegundos.
    let lockIntervalId; // Variável para armazenar o ID do intervalo de renovação.

    const formProcesso = document.getElementById('form-processo'); // O formulário de processo.

    // Tenta adquirir o lock ou renová-lo se já o possuir.
    async function acquireAndRenewLock() {
        try {
            const csrfToken = document.querySelector('input[name="csrf_token"]').value;
            const response = await fetch(FlaskRoutes.apiAcquireLock, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-Requested-With': 'XMLHttpRequest'
                },
                body: JSON.stringify({
                    table_name: 'processos',
                    record_id: currentProcessId,
                    csrf_token: csrfToken
                })
            });
            const data = await response.json();

            if (!data.success) {
                showToast(data.type || 'warning', data.message || 'Falha ao adquirir bloqueio de edição.');
                console.warn('initializeRecordLocking: Bloqueio falhou:', data.message);
                formProcesso.querySelectorAll('input, select, textarea, button[type="submit"]').forEach(el => el.disabled = true);
                clearInterval(lockIntervalId);
            } else {
                console.log('initializeRecordLocking: Bloqueio adquirido/renovado com sucesso.');
                if (!lockIntervalId) {
                    lockIntervalId = setInterval(renewLock, renewInterval);
                    console.log(`initializeRecordLocking: Renovação de bloqueio agendada a cada ${renewInterval / 1000} segundos.`);
                }
            }
        } catch (error) {
            console.error('initializeRecordLocking: Erro na requisição de aquisição/renovação de bloqueio:', error);
            showToast('danger', 'Erro de comunicação ao tentar gerenciar o bloqueio.');
            formProcesso.querySelectorAll('input, select, textarea, button[type="submit"]').forEach(el => el.disabled = true);
            clearInterval(lockIntervalId);
        }
    }

    // Tenta renovar o lock existente.
    async function renewLock() {
        try {
            const csrfToken = document.querySelector('input[name="csrf_token"]').value;
            const response = await fetch(FlaskRoutes.apiRenewLock, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-Requested-With': 'XMLHttpRequest'
                },
                body: JSON.stringify({
                    table_name: 'processos',
                    record_id: currentProcessId,
                    csrf_token: csrfToken
                })
            });
            const data = await response.json();
            if (!data.success) {
                console.warn('initializeRecordLocking: Alerta de Bloqueio:', data.message);
                if (data.message && (data.message.includes("perdido") || data.message.includes("outro usuário"))) {
                    showToast('warning', 'Seu bloqueio de edição foi perdido. Outro usuário pode ter assumido a edição ou sua sessão expirou. Salve suas alterações rapidamente ou recarregue a página.');
                    formProcesso.querySelectorAll('input, select, textarea, button[type="submit"]').forEach(el => el.disabled = true);
                    clearInterval(lockIntervalId);
                }
            }
        } catch (error) {
            console.error('initializeRecordLocking: Erro na requisição de renovação de bloqueio:', error);
            showToast('danger', 'Erro de comunicação ao tentar renovar o bloqueio.');
            formProcesso.querySelectorAll('input, select, textarea, button[type="submit"]').forEach(el => el.disabled = true);
            clearInterval(lockIntervalId);
        }
    }

    // Libera o lock quando o usuário está prestes a sair da página.
    async function releaseLockOnUnload() {
        const formData = new FormData();
        formData.append('table_name', 'processos');
        formData.append('record_id', currentProcessId);
        formData.append('csrf_token', document.querySelector('input[name="csrf_token"]').value);

        // `sendBeacon` é otimizado para enviar dados de forma não-bloqueante no final da sessão do usuário.
        navigator.sendBeacon(FlaskRoutes.apiReleaseLock, formData);
        console.log('initializeRecordLocking: Bloqueio enviado para liberação via sendBeacon ao descarregar a página.');
    }

    acquireAndRenewLock();

    window.addEventListener('beforeunload', releaseLockOnUnload);

    // Lógica do botão "Cancelar" no formulário de edição.
    const cancelButton = document.getElementById('cancelButton');
    if (cancelButton) {
        cancelButton.addEventListener('click', async function(e) {
            e.preventDefault();

            window.removeEventListener('beforeunload', releaseLockOnUnload);
            clearInterval(lockIntervalId);

            try {
                const csrfToken = document.querySelector('input[name="csrf_token"]').value;
                const response = await fetch(FlaskRoutes.apiReleaseLock, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'X-Requested-With': 'XMLHttpRequest'
                    },
                    body: JSON.stringify({
                        table_name: 'processos',
                        record_id: currentProcessId,
                        csrf_token: csrfToken
                    })
                });
                const data = await response.json();
                if (data.success) {
                    console.log('initializeRecordLocking: Bloqueio liberado com sucesso ao cancelar.');
                    showToast('info', 'Edição cancelada. O processo foi liberado.');
                } else {
                    console.warn('initializeRecordLocking: Falha ao liberar bloqueio ao cancelar:', data.message);
                    showToast('warning', 'Edição cancelada, mas o bloqueio pode não ter sido liberado. ' + data.message);
                }
            } catch (error) {
                console.error('initializeRecordLocking: Erro ao liberar bloqueio via AJAX ao cancelar:', error);
                showToast('danger', 'Erro na comunicação ao tentar liberar o bloqueio. Tente novamente.');
            } finally {
                const redirectUrl = FlaskRoutes.processosVisualizarBase.replace('_ID_', currentProcessId);
                setTimeout(() => {
                    window.location.href = redirectUrl;
                }, 500);
            }
        });
    }
}