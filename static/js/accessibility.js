/* RegistroFácil — navegação de teclado, foco consistente e semântica interativa */
(function () {
    'use strict';

    const isEditable = (element) => {
        if (!element) return false;
        return ['INPUT', 'SELECT', 'TEXTAREA'].includes(element.tagName);
    };

    const isVisible = (element) => {
        if (!element || element.disabled || element.type === 'hidden') return false;
        const style = window.getComputedStyle(element);
        return style.display !== 'none' && style.visibility !== 'hidden';
    };

    const focusableSelector = [
        'input:not([type="hidden"]):not([disabled])',
        'select:not([disabled])',
        'textarea:not([disabled])',
        'button:not([disabled])',
        'a[href]',
        '[tabindex]:not([tabindex="-1"])'
    ].join(',');

    function focusNextField(current) {
        const form = current.form;
        if (!form) return false;
        const fields = Array.from(form.querySelectorAll(focusableSelector))
            .filter(isVisible)
            .filter((element) => !element.matches('[data-skip-enter]'));
        const index = fields.indexOf(current);
        if (index < 0 || index >= fields.length - 1) return false;
        const next = fields.slice(index + 1).find((element) => (
            element.matches('input, select, textarea') || element.matches('[data-enter-target]')
        ));
        if (!next) return false;
        current.setAttribute('data-enter-navigation', 'true');
        next.focus({ preventScroll: true });
        next.scrollIntoView({ block: 'nearest', behavior: 'smooth' });
        return true;
    }

    function openPicker(element) {
        try {
            if (typeof element.showPicker === 'function') {
                element.showPicker();
                return true;
            }
        } catch (_) { /* O navegador pode bloquear showPicker fora da ação direta. */ }
        if (element.matches('select, [data-bs-toggle="dropdown"]')) element.click();
        return true;
    }

    function initializeMenuItems() {
        document.querySelectorAll('.menu-item[data-href], .menu-item[data-bs-toggle="modal"]').forEach((item) => {
            if (!item.hasAttribute('tabindex')) item.setAttribute('tabindex', '0');
            if (!item.hasAttribute('role')) item.setAttribute('role', 'button');
            const label = item.querySelector('.menu-text')?.textContent?.trim();
            if (label && !item.hasAttribute('aria-label')) item.setAttribute('aria-label', label);
            item.addEventListener('keydown', (event) => {
                if (event.key === 'Enter' || event.key === ' ') {
                    event.preventDefault();
                    item.click();
                }
            });
        });
    }

    function initializeMobileMenu() {
        const button = document.getElementById('mobile-menu-btn');
        const sidebar = document.getElementById('sidebar');
        if (!button || !sidebar) return;
        const syncState = () => {
            const isOpen = sidebar.classList.contains('mobile-open');
            button.setAttribute('aria-expanded', String(isOpen));
            button.setAttribute('aria-label', isOpen ? 'Fechar menu' : 'Abrir menu');
            sidebar.setAttribute('aria-hidden', window.innerWidth <= 991 ? String(!isOpen) : 'false');
        };
        const observer = new MutationObserver(syncState);
        observer.observe(sidebar, { attributes: true, attributeFilter: ['class'] });
        syncState();
        window.addEventListener('resize', syncState, { passive: true });
        document.getElementById('sidebar-overlay')?.addEventListener('click', () => {
            window.setTimeout(syncState, 0);
            button.focus({ preventScroll: true });
        });
        document.addEventListener('keydown', (event) => {
            if (event.key === 'Escape' && sidebar.classList.contains('mobile-open')) {
                window.closeMobileSidebar?.();
                button.focus({ preventScroll: true });
            }
        });
    }

    function initializeKeyboardNavigation() {
        document.addEventListener('keydown', function (event) {
            const target = event.target;
            if (!target || target.isContentEditable) return;
            if (target.matches('select')) {
                if (['Enter', ' ', 'ArrowDown'].includes(event.key)) {
                    event.preventDefault();
                    openPicker(target);
                }
                return;
            }
            if (target.matches('.dropdown-toggle, [data-bs-toggle="dropdown"]')) {
                if (['Enter', ' ', 'ArrowDown'].includes(event.key)) {
                    event.preventDefault();
                    target.click();
                }
                return;
            }
            if (!isEditable(target) || target.tagName === 'TEXTAREA' || event.key !== 'Enter') return;
            if (target.closest('[data-enter-submit], .enter-submit')) return;
            if (target.type === 'search' && target.form?.querySelectorAll('input, select, textarea').length === 1) return;
            if (focusNextField(target)) event.preventDefault();
        });

        document.addEventListener('focusin', function (event) {
            const target = event.target;
            if (target.matches('select, [data-bs-toggle="dropdown"], [data-open-dropdown-on-focus]')) openPicker(target);
        });

        initializeMenuItems();
        initializeMobileMenu();
        document.querySelector('.skip-link')?.addEventListener('click', () => {
            document.getElementById('main-content')?.focus({ preventScroll: true });
        });
    }

    if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', initializeKeyboardNavigation);
    else initializeKeyboardNavigation();
})();
