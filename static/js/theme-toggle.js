/* Controle global do modo claro/escuro sem FOUC. */
(function () {
    'use strict';

    const STORAGE_KEY = 'rf-theme-mode';
    const LEGACY_STORAGE_KEY = 'registrofacil-theme';

    function resolveTheme(mode) {
        if (mode === 'dark' || mode === 'light') return mode;
        return window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches
            ? 'dark'
            : 'light';
    }

    function updateIcon() {
        const button = document.getElementById('theme-toggle-btn');
        const icon = document.getElementById('theme-icon') || button?.querySelector('i');
        if (!button || !icon) return;

        const current = document.documentElement.getAttribute('data-theme') || 'light';
        icon.className = current === 'dark' ? 'bi bi-sun-fill' : 'bi bi-moon-fill';
        button.title = current === 'dark' ? 'Ativar tema claro' : 'Ativar tema escuro';
        button.setAttribute('aria-label', current === 'dark'
            ? 'Ativar tema claro'
            : 'Ativar tema escuro');
    }

    function finishPreload() {
        const html = document.documentElement;
        html.classList.remove('rf-preload');
        html.classList.add('rf-loaded');
    }

    function applyTheme(mode, persist = true) {
        const normalized = ['light', 'dark', 'auto'].includes(mode) ? mode : 'auto';
        const html = document.documentElement;
        html.setAttribute('data-theme', resolveTheme(normalized));
        html.setAttribute('data-theme-mode', normalized);

        if (persist) {
            try {
                localStorage.setItem(STORAGE_KEY, normalized);
                localStorage.removeItem(LEGACY_STORAGE_KEY);
            } catch (error) {
                // A preferência visual continua funcionando mesmo sem localStorage.
            }
        }

        updateIcon();
        document.dispatchEvent(new CustomEvent('themeChanged', {
            detail: { mode: normalized, theme: html.getAttribute('data-theme') }
        }));
    }

    function toggleTheme() {
        const current = document.documentElement.getAttribute('data-theme') || 'light';
        applyTheme(current === 'dark' ? 'light' : 'dark');

        if (typeof window.showToast === 'function') {
            window.showToast({
                type: 'info',
                title: 'Aparência atualizada',
                message: current === 'dark' ? 'Tema claro ativado.' : 'Tema escuro ativado.'
            });
        }
    }

    function createToggleButton() {
        let button = document.getElementById('theme-toggle-btn');
        if (button) return button;

        const navbarActions = document.querySelector('.navbar .ms-auto') || document.querySelector('.navbar');
        if (!navbarActions) return null;

        button = document.createElement('button');
        button.id = 'theme-toggle-btn';
        button.type = 'button';
        button.className = 'nav-btn nav-btn-secondary theme-toggle';
        button.innerHTML = '<i id="theme-icon" class="bi bi-moon-fill" aria-hidden="true"></i>';
        navbarActions.prepend(button);
        return button;
    }

    function init() {
        const button = createToggleButton();
        if (button && !button.dataset.themeBound) {
            button.addEventListener('click', toggleTheme);
            button.dataset.themeBound = 'true';
        }

        updateIcon();
        finishPreload();

        document.addEventListener('keydown', (event) => {
            if ((event.ctrlKey || event.metaKey) && event.shiftKey && event.key.toLowerCase() === 't') {
                event.preventDefault();
                toggleTheme();
            }
        });

        if (window.matchMedia) {
            const media = window.matchMedia('(prefers-color-scheme: dark)');
            const onChange = () => {
                if (document.documentElement.getAttribute('data-theme-mode') === 'auto') {
                    applyTheme('auto', false);
                }
            };
            if (media.addEventListener) media.addEventListener('change', onChange);
            else if (media.addListener) media.addListener(onChange);
        }
    }

    window.toggleTheme = toggleTheme;
    window.applyTheme = applyTheme;
    window.setTheme = (mode) => applyTheme(mode);
    window.getTheme = () => document.documentElement.getAttribute('data-theme') || 'light';

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init, { once: true });
    } else {
        init();
    }
})();
