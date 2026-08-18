/* Feedback não bloqueante para as telas públicas de autenticação. */
(function () {
    function ensureIndicator() {
        let indicator = document.getElementById('rf-auth-loading');
        if (indicator) return indicator;
        indicator = document.createElement('div');
        indicator.id = 'rf-auth-loading';
        indicator.setAttribute('role', 'status');
        indicator.setAttribute('aria-live', 'polite');
        indicator.setAttribute('aria-label', 'Processando autenticação');
        document.body.prepend(indicator);
        return indicator;
    }

    function show(message) {
        const indicator = ensureIndicator();
        indicator.dataset.message = message || 'Processando...';
        indicator.classList.add('is-visible');
    }

    document.addEventListener('DOMContentLoaded', function () {
        const indicator = ensureIndicator();
        document.querySelectorAll('form[id$="Form"], form[id$="form"]').forEach(function (form) {
            form.addEventListener('submit', function (event) {
                if (event.defaultPrevented || form.dataset.authSubmitting === 'true') return;
                form.dataset.authSubmitting = 'true';
                show(form.dataset.loadingMessage || 'Processando...');
            });
        });
        window.addEventListener('pageshow', function () {
            indicator.classList.remove('is-visible');
        });
    });
})();
