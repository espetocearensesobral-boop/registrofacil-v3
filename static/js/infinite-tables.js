/*
 * Registro Fácil — carregamento contínuo das listas padronizadas.
 * A API existente continua usando paginação server-side internamente; a
 * interface apenas consome os lotes seguintes por rolagem, sem exibir páginas.
 */
(function () {
    'use strict';

    const LIST_SELECTOR = '[data-infinite-scroll]';
    const FETCH_TIMEOUT_MS = 20000;

    function asNumber(value, fallback) {
        const parsed = Number.parseInt(value, 10);
        return Number.isFinite(parsed) ? parsed : fallback;
    }

    function pluralizeRegistro(total) {
        return `${total} registro${total === 1 ? '' : 's'}`;
    }

    function getRowsFromResponse(html) {
        const documentFromResponse = new DOMParser().parseFromString(html, 'text/html');
        const list = documentFromResponse.querySelector(LIST_SELECTOR);
        const tbody = list && list.querySelector('tbody');
        return {
            rows: tbody ? Array.from(tbody.querySelectorAll('tr')) : [],
            nextTotal: list ? asNumber(list.dataset.totalRecords, null) : null,
            nextTotalPages: list ? asNumber(list.dataset.totalPages, null) : null
        };
    }

    function initInfiniteList(list) {
        if (!list || list.dataset.infiniteReady === 'true') return;

        const scrollViewport = list;
        const table = list.querySelector('table');
        const tbody = table && table.querySelector('tbody');
        const sentinel = list.querySelector('[data-infinite-sentinel]');
        const status = list.querySelector('[data-infinite-status]');
        if (!tbody || !sentinel) return;

        list.dataset.infiniteReady = 'true';
        let currentPage = asNumber(list.dataset.page, 1);
        const totalPages = asNumber(list.dataset.totalPages, 1);
        const pageSize = Math.max(1, asNumber(list.dataset.pageSize, 50));
        const pageSizeParam = list.dataset.pageSizeParam || 'registros_por_pagina';
        const endpoint = list.dataset.infiniteEndpoint || window.location.pathname;
        let totalRecords = asNumber(list.dataset.totalRecords, tbody.querySelectorAll('tr').length);
        let loadedRecords = tbody.querySelectorAll('tr').length;
        let loading = false;
        let completed = currentPage >= totalPages;
        let observer = null;

        function updateStatus(message, visible) {
            if (!status) return;
            status.textContent = message || '';
            status.hidden = !visible;
        }

        function finish() {
            completed = true;
            sentinel.hidden = true;
            updateStatus(`${pluralizeRegistro(totalRecords)} carregado${totalRecords === 1 ? '' : 's'}.`, true);
            if (observer) observer.disconnect();
        }

        function hasRoomToScroll() {
            return scrollViewport.scrollHeight <= scrollViewport.clientHeight + 8;
        }

        async function loadNextPage() {
            if (loading || completed) return;
            loading = true;
            sentinel.hidden = false;
            updateStatus('Carregando mais registros…', true);

            const nextPage = currentPage + 1;
            const params = new URLSearchParams(window.location.search);
            params.set('pagina', String(nextPage));
            params.set(pageSizeParam, String(pageSize));

            const controller = new AbortController();
            const timeout = window.setTimeout(() => controller.abort(), FETCH_TIMEOUT_MS);
            try {
                const response = await fetch(`${endpoint}?${params.toString()}`, {
                    method: 'GET',
                    headers: { 'X-Requested-With': 'XMLHttpRequest', 'Accept': 'text/html' },
                    credentials: 'same-origin',
                    signal: controller.signal
                });
                if (!response.ok) throw new Error(`HTTP ${response.status}`);

                const payload = getRowsFromResponse(await response.text());
                payload.rows.forEach((row) => tbody.appendChild(row));
                loadedRecords += payload.rows.length;
                if (payload.nextTotal !== null) totalRecords = payload.nextTotal;
                currentPage = nextPage;

                if (payload.nextTotalPages !== null && payload.nextTotalPages <= currentPage) {
                    finish();
                } else if (currentPage >= totalPages || loadedRecords >= totalRecords || payload.rows.length === 0) {
                    finish();
                } else {
                    updateStatus('', false);
                    sentinel.hidden = false;
                    // Listas curtas precisam preencher o viewport sem exigir um
                    // gesto artificial de rolagem para disparar o próximo lote.
                    if (hasRoomToScroll()) window.requestAnimationFrame(loadNextPage);
                }
            } catch (error) {
                console.error('[Registro Fácil] Falha ao carregar registros adicionais:', error);
                updateStatus('Não foi possível carregar mais registros. Tente rolar novamente.', true);
                sentinel.hidden = false;
            } finally {
                window.clearTimeout(timeout);
                loading = false;
            }
        }

        if (completed) {
            finish();
            return;
        }

        observer = 'IntersectionObserver' in window
            ? new IntersectionObserver((entries) => {
                if (entries.some((entry) => entry.isIntersecting)) loadNextPage();
            }, { root: scrollViewport, rootMargin: '240px 0px', threshold: 0.01 })
            : null;

        sentinel.hidden = false;
        if (observer) observer.observe(sentinel);
        scrollViewport.addEventListener('scroll', function () {
            const remaining = scrollViewport.scrollHeight - scrollViewport.scrollTop - scrollViewport.clientHeight;
            if (remaining < 240) loadNextPage();
        }, { passive: true });

        updateStatus('', false);
        if (hasRoomToScroll()) window.requestAnimationFrame(loadNextPage);
    }

    function boot() {
        document.querySelectorAll(LIST_SELECTOR).forEach(initInfiniteList);
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', boot, { once: true });
    } else {
        boot();
    }
})();
