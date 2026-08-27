/* Navegação parcial para telas autenticadas: preserva a shell e evita recarregar a página inteira. */

function isInternalPage(url) {
    return url.origin === window.location.origin && url.protocol === window.location.protocol;
}

function copyPageScript(script) {
    return new Promise((resolve, reject) => {
        const replacement = document.createElement('script');
        for (const attribute of script.attributes) replacement.setAttribute(attribute.name, attribute.value);
        replacement.textContent = script.textContent;
        const nativeAddEventListener = document.addEventListener;
        const restoreDocumentEvents = () => {
            document.addEventListener = nativeAddEventListener;
        };
        document.addEventListener = function(type, listener, options) {
            if (type === 'DOMContentLoaded') {
                queueMicrotask(() => listener.call(document, new Event('DOMContentLoaded')));
                return;
            }
            return nativeAddEventListener.call(document, type, listener, options);
        };
        replacement.addEventListener('load', () => {
            restoreDocumentEvents();
            resolve();
        }, { once: true });
        replacement.addEventListener('error', () => {
            restoreDocumentEvents();
            reject();
        }, { once: true });
        document.body.appendChild(replacement);
        if (!replacement.src) {
            restoreDocumentEvents();
            resolve();
        }
    });
}

async function runPageScripts(scripts) {
    for (const script of scripts) {
        try {
            await copyPageScript(script);
        } catch (_) {
            // Uma falha de recurso específico não deve impedir a navegação já concluída.
        }
    }
}

function updateNavigationState() {
    document.dispatchEvent(new CustomEvent('rf:page-change'));
    window.rfUpdateProcessFilterBadge?.();
    window.closeMobileSidebar?.();
}

async function navigate(url, { replace = false } = {}) {
    const destination = new URL(url, window.location.href);
    if (!isInternalPage(destination)) {
        window.location.assign(destination.href);
        return;
    }

    window.showPageLoading?.('Abrindo...');
    try {
        const response = await fetch(destination.href, {
            credentials: 'same-origin',
            headers: { 'X-Requested-With': 'XMLHttpRequest' },
        });
        if (!response.ok) throw new Error(`Resposta ${response.status}`);

        const page = new DOMParser().parseFromString(await response.text(), 'text/html');
        const nextWrapper = page.getElementById('page-content-wrapper');
        const currentWrapper = document.getElementById('page-content-wrapper');
        if (!nextWrapper || !currentWrapper) throw new Error('Estrutura de página incompatível');

        const pageScripts = [...nextWrapper.querySelectorAll('script')].map(script => script.cloneNode(true));
        nextWrapper.querySelectorAll('script').forEach(script => script.remove());
        currentWrapper.replaceWith(nextWrapper);

        document.title = page.title || document.title;
        const historyMethod = replace ? 'replaceState' : 'pushState';
        window.history[historyMethod]({}, '', destination.href);
        window.scrollTo({ top: 0, behavior: 'auto' });
        updateNavigationState();
        await runPageScripts(pageScripts);
        document.getElementById('main-content')?.focus({ preventScroll: true });
    } catch (error) {
        window.location.assign(destination.href);
    } finally {
        window.hidePageLoading?.();
    }
}

window.rfNavigate = navigate;

document.addEventListener('click', event => {
    const link = event.target.closest('a[data-rf-soft-nav]');
    if (!link || event.defaultPrevented || event.button !== 0 || event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) return;
    event.preventDefault();
    navigate(link.href);
});

document.addEventListener('submit', event => {
    const form = event.target.closest('form.process-filter-toolbar[method="get"]');
    if (!form || event.defaultPrevented) return;
    event.preventDefault();
    const destination = new URL(form.action, window.location.href);
    const fields = new FormData(form);
    for (const [name, value] of fields.entries()) {
        if (String(value).trim()) destination.searchParams.set(name, value);
    }
    navigate(destination.href);
});

window.addEventListener('popstate', () => navigate(window.location.href, { replace: true }));
