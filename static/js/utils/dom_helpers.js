// registrofacil/static/js/utils/dom_helpers.js

/**
 * Motor global de notificações.
 * Aceita o contrato novo (showToast(message, {type, title})) e as duas
 * assinaturas legadas: showToast(type, message) e showToast(message, type).
 */
const NOTIFICATION_TYPES = new Set(['success', 'danger', 'warning', 'info']);
const NOTIFICATION_META = {
    success: { label: 'Sucesso', icon: 'check-circle-fill', fallback: 'Operação concluída com sucesso.' },
    danger: { label: 'Erro', icon: 'x-circle-fill', fallback: 'Não foi possível concluir a operação. Tente novamente.' },
    warning: { label: 'Atenção', icon: 'exclamation-triangle-fill', fallback: 'Atenção: verifique os dados e tente novamente.' },
    info: { label: 'Informação', icon: 'info-circle-fill', fallback: 'Informação do sistema.' }
};

function escapeHtml(value) {
    return String(value ?? '').replace(/[&<>'"]/g, (char) => ({
        '&': '&amp;', '<': '&lt;', '>': '&gt;', "'": '&#39;', '"': '&quot;'
    }[char]));
}

export function normalizeNotification(first, second, third) {
    let payload = first;
    let type = third || 'info';
    let title = '';
    let message = '';

    if (first && typeof first === 'object') {
        payload = first;
        type = payload.type || (payload.success === false ? 'danger' : 'info');
        title = payload.title || '';
        message = payload.message || payload.error || '';
    } else if (NOTIFICATION_TYPES.has(String(first))) {
        // Contrato legado: (type, message)
        type = String(first);
        message = second;
    } else if (NOTIFICATION_TYPES.has(String(second))) {
        // Assinatura invertida existente: (message, type)
        message = first;
        type = String(second);
    } else {
        // Contrato preferencial: (message, {type, title})
        message = first;
        if (second && typeof second === 'object') {
            type = second.type || type;
            title = second.title || '';
        }
    }

    type = NOTIFICATION_TYPES.has(String(type)) ? String(type) : 'info';
    const meta = NOTIFICATION_META[type];
    message = String(message || '').trim() || meta.fallback;
    title = String(title || '').trim() || meta.label;
    return { type, title, message, ...meta };
}

export function showToast(first, second, third) {
    const notification = normalizeNotification(first, second, third);
    const toastContainer = document.querySelector('.toast-container');
    if (!toastContainer) {
        console.warn('showToast: container ausente; notificação:', notification);
        return notification;
    }

    const toast = document.createElement('div');
    toast.className = `toast notification-toast notification-${notification.type}`;
    toast.setAttribute('role', notification.type === 'danger' ? 'alert' : 'status');
    toast.setAttribute('aria-live', notification.type === 'danger' ? 'assertive' : 'polite');
    toast.innerHTML = `
        <div class="toast-header">
            <i class="bi bi-${notification.icon} notification-icon" aria-hidden="true"></i>
            <strong class="me-auto">${escapeHtml(notification.title)}</strong>
            <button type="button" class="btn-close" data-bs-dismiss="toast" aria-label="Fechar notificação"></button>
        </div>
        <div class="toast-body">${escapeHtml(notification.message)}</div>`;
    toastContainer.appendChild(toast);

    if (window.bootstrap?.Toast) {
        const instance = new bootstrap.Toast(toast, { delay: notification.type === 'danger' ? 8000 : 5000 });
        instance.show();
        toast.addEventListener('hidden.bs.toast', () => toast.remove(), { once: true });
    } else {
        toast.classList.add('show');
        setTimeout(() => toast.remove(), 5000);
    }
    return notification;
}

export function showResponseToast(response, fallbackMessage = '') {
    const data = response?.data || response || {};
    return showToast({
        type: data.type || (data.success === false || response?.status >= 400 ? 'danger' : 'success'),
        title: data.title,
        message: data.message || data.error || fallbackMessage
    });
}

/**
 * Converte bytes para um formato legível (KB, MB, GB).
 * @param {number} bytes - O número de bytes.
 * @param {number} [decimals=2] - Número de casas decimais.
 * @returns {string} - String formatada (ex: "1.23 MB").
 */
export function formatBytes(bytes, decimals = 2) {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const dm = decimals < 0 ? 0 : decimals;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(dm)) + ' ' + sizes[i];
}

/**
 * Valida um endereço de e-mail.
 * @param {string} email - O e-mail a ser validado.
 * @returns {boolean} - True se o e-mail for válido, false caso contrário.
 */
export function isValidEmail(email) {
    return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email);
}

/**
 * Valida um número de telefone.
 * @param {string} phone - O telefone a ser validado.
 * @returns {boolean} - True se o telefone for válido, false caso contrário.
 */
export function isValidPhone(phone) {
    // Esta regex permite formatos como (XX) XXXX-XXXX e (XX) XXXXX-XXXX com espaços ou hifens
    const padrao = /^\(?[0-9]{2}\)?[ .-]?[0-9]{4,5}[ .-][0-9]{4}$/;
    return padrao.test(phone);
}


/**
 * Aplica a máscara de telefone (XX) XXXXX-XXXX ou (XX) XXXX-XXXX.
 * @param {string} value - O valor do campo (apenas números).
 * @returns {string} - O valor formatado com a máscara.
 */
export function formatPhoneNumber(value) {
    value = value.replace(/\D/g, ''); // Remove tudo que não é dígito
    if (value.length > 11) {
        value = value.substring(0, 11); // Limita a 11 dígitos
    }

    if (value.length > 10) { // Celular com 9 dígitos: (XX) 9XXXX-XXXX
        return value.replace(/^(\d{2})(\d{5})(\d{4})$/, "($1) $2-$3");
    } else if (value.length > 6) { // Fixo ou celular antigo: (XX) XXXX-XXXX
        return value.replace(/^(\d{2})(\d{4})(\d{4})$/, "($1) $2-$3");
    } else if (value.length > 2) { // Apenas o DDD: (XX) XXXX
        return value.replace(/^(\d{2})(\d+)$/, "($1) $2");
    } else if (value.length > 0) { // Menos que o DDD completo
        return `(${value}`;
    }
    return value;
}


/**
 * Valida uma matrícula.
 * @param {string} matricula - A matrícula a ser validada.
 * @returns {boolean} - True se a matrícula for válida, false caso contrário.
 */
    export function isValidMatricula(matricula) {
    // A regex agora inclui ^ e $ para garantir que a string inteira corresponda ao padrão.
    // Isso evita que strings como "abc!@#" passem na validação se "abc" for válido.
    return /^[A-Za-z0-9\s\-\.\/]{1,50}$/.test(matricula);
}

/**
 * Valida se uma data é futura ou igual à data de hoje.
 * @param {string} dateString - A string da data no formato YYYY-MM-DD.
 * @returns {boolean} - True se a data for futura ou hoje, false caso contrário.
 */
export function isValidFutureOrTodayDate(dateString) {
    const selectedDate = new Date(dateString + 'T00:00:00'); // Garante que a hora seja 00:00:00 GMT
    const today = new Date();
    today.setHours(0, 0, 0, 0); // Zera a hora para comparar apenas a data (no fuso local)

    // Para garantir que a comparação seja precisa e não dependa do fuso horário na criação da data
    // Formatamos today para o mesmo formato YYYY-MM-DD que o dateString
    const year = today.getFullYear();
    const month = String(today.getMonth() + 1).padStart(2, '0');
    const day = String(today.getDate()).padStart(2, '0');
    const todayFormatted = `${year}-${month}-${day}`;
    
    // Compara as datas já normalizadas para o início do dia
    return selectedDate >= new Date(todayFormatted + 'T00:00:00');
}

/**
 * Alterna a visibilidade de um campo de senha.
 * @param {string} id - O ID do campo de input da senha.
 */
export function togglePassword(id) {
    const input = document.getElementById(id);
    const icon = input.parentElement.querySelector('.toggle-icon i');
    if (input.type === 'password') {
        input.type = 'text';
        icon.classList.remove('bi-eye');
        icon.classList.add('bi-eye-slash');
    } else {
        input.type = 'password';
        icon.classList.remove('bi-eye-slash');
        icon.classList.add('bi-eye');
    }
}
// Removido: window.togglePassword = togglePassword; // Expõe a função globalmente para chamadas onclick, pois já é exportada.
