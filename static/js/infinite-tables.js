/*
 * Registro Fácil — carregamento incremental das listas padronizadas.
 *
 * As listas comuns continuam consumindo lotes pela rolagem de seu wrapper.
 * Todos os Processos usa o modo "internal-first" apenas como marcador de
 * comportamento: a tabela não ganha uma segunda barra vertical; o carregamento
 * é disparado pelo scroll natural do documento, como em interfaces móveis.
 */
(function () {
    'use strict';

    const LIST_SELECTOR = '[data-infinite-scroll]';
    const FETCH_TIMEOUT_MS = 20000;
    const LOAD_THRESHOLD = 360;

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

        const table = list.querySelector('table');
        const tbody = table && table.querySelector('tbody');
        const sentinel = list.querySelector('[data-infinite-sentinel]');
        const status = list.querySelector('[data-infinite-status]');
        if (!tbody || !sentinel) return;

        list.dataset.infiniteReady = 'true';
        const naturalPageScroll = list.dataset.listScrollMode === 'internal-first';
        let currentPage = asNumber(list.dataset.page, 1);
        let totalPages = asNumber(list.dataset.totalPages, 1);
        const pageSize = Math.max(1, asNumber(list.dataset.pageSize, naturalPageScroll ? 10 : 50));
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
            if (naturalPageScroll) window.removeEventListener('scroll', onWindowScroll);
        }

        function internalViewportHasRoom() {
            return list.scrollHeight <= list.clientHeight + 8;
        }

        function documentHasRoomToScroll() {
            return document.documentElement.scrollHeight > document.documentElement.clientHeight + 8;
        }

        function documentNearEnd() {
            return window.innerHeight + window.scrollY >= document.documentElement.scrollHeight - LOAD_THRESHOLD;
        }

        function onWindowScroll() {
            if (!naturalPageScroll || completed || loading) return;
            if (documentNearEnd()) loadNextPage();
        }

        async function loadNextPage() {
            if (loading || completed) return;
            loading = true;
            if (!naturalPageScroll) sentinel.hidden = false;
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
                if (payload.nextTotalPages !== null) totalPages = payload.nextTotalPages;
                currentPage = nextPage;

                if (currentPage >= totalPages || loadedRecords >= totalRecords || payload.rows.length === 0) {
                    finish();
                } else if (naturalPageScroll) {
                    updateStatus('', false);
                    sentinel.hidden = true;
                    // Se o lote ainda não criou altura suficiente para a página,
                    // carrega outro lote para evitar uma tela sem scroll.
                    if (!documentHasRoomToScroll() || documentNearEnd()) {
                        window.requestAnimationFrame(loadNextPage);
                    }
                } else {
                    updateStatus('', false);
                    sentinel.hidden = false;
                    if (internalViewportHasRoom()) window.requestAnimationFrame(loadNextPage);
                }
            } catch (error) {
                console.error('[Registro Fácil] Falha ao carregar registros adicionais:', error);
                updateStatus('Não foi possível carregar mais registros. Tente rolar novamente.', true);
                if (!naturalPageScroll) sentinel.hidden = false;
            } finally {
                window.clearTimeout(timeout);
                loading = false;
            }
        }

        if (completed) {
            finish();
            return;
        }

        if (naturalPageScroll) {
            sentinel.hidden = true;
            window.addEventListener('scroll', onWindowScroll, { passive: true });
            updateStatus('', false);
            // O primeiro lote permanece visível até o usuário iniciar a
            // rolagem; o próximo lote só entra ao alcançar o fim da página.
            return;
        }

        observer = 'IntersectionObserver' in window
            ? new IntersectionObserver((entries) => {
                if (entries.some((entry) => entry.isIntersecting)) loadNextPage();
            }, { root: list, rootMargin: '240px 0px', threshold: 0.01 })
            : null;
        sentinel.hidden = false;
        if (observer) observer.observe(sentinel);
        list.addEventListener('scroll', function () {
            const remaining = list.scrollHeight - list.scrollTop - list.clientHeight;
            if (remaining < 240) loadNextPage();
        }, { passive: true });
        updateStatus('', false);
        if (internalViewportHasRoom()) window.requestAnimationFrame(loadNextPage);
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
