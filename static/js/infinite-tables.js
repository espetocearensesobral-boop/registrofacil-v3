/*
 * Registro Fácil — carregamento contínuo das listas padronizadas.
 *
 * O modo padrão mantém a rolagem interna das tabelas. A lista de Todos os
 * Processos pode ativar o modo experimental "internal-first": começa com
 * dez registros em uma viewport própria e, ao atingir o fim do lote inicial,
 * libera o crescimento da tabela e transfere a continuidade para o scroll da
 * página principal.
 */
(function () {
    'use strict';

    const LIST_SELECTOR = '[data-infinite-scroll]';
    const FETCH_TIMEOUT_MS = 20000;
    const MAIN_SCROLL_THRESHOLD = 240;

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
        const isInternalFirst = list.dataset.listScrollMode === 'internal-first';
        const mainContent = document.getElementById('main-content');
        const card = list.closest('.process-list-card');
        let currentPage = asNumber(list.dataset.page, 1);
        let totalPages = asNumber(list.dataset.totalPages, 1);
        const pageSize = Math.max(1, asNumber(list.dataset.pageSize, isInternalFirst ? 10 : 50));
        const pageSizeParam = list.dataset.pageSizeParam || 'registros_por_pagina';
        const endpoint = list.dataset.infiniteEndpoint || window.location.pathname;
        let totalRecords = asNumber(list.dataset.totalRecords, tbody.querySelectorAll('tr').length);
        let loadedRecords = tbody.querySelectorAll('tr').length;
        let loading = false;
        let completed = currentPage >= totalPages;
        let mainScrollActive = false;
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
            window.removeEventListener('scroll', onWindowScroll);
        }

        function hasRoomToScroll() {
            return scrollViewport.scrollHeight <= scrollViewport.clientHeight + 8;
        }

        function activateMainScroll() {
            if (!isInternalFirst || mainScrollActive) return;
            mainScrollActive = true;
            list.classList.add('rf-main-scroll-active');
            if (card) card.classList.add('rf-main-scroll-active');
            if (mainContent) mainContent.classList.add('rf-main-scroll-active');
            if (observer) {
                observer.disconnect();
                observer = null;
            }
            window.addEventListener('scroll', onWindowScroll, { passive: true });
            updateStatus('Continue rolando a página para carregar mais registros.', true);
        }

        function nearMainScrollEnd() {
            return window.innerHeight + window.scrollY >= document.documentElement.scrollHeight - MAIN_SCROLL_THRESHOLD;
        }

        function onWindowScroll() {
            if (!mainScrollActive || completed || !nearMainScrollEnd()) return;
            loadNextPage();
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
                if (payload.nextTotalPages !== null) totalPages = payload.nextTotalPages;
                currentPage = nextPage;

                if (currentPage >= totalPages || loadedRecords >= totalRecords || payload.rows.length === 0) {
                    finish();
                } else {
                    updateStatus(mainScrollActive ? 'Continue rolando a página para carregar mais registros.' : '', mainScrollActive);
                    sentinel.hidden = false;
                    if (!mainScrollActive && hasRoomToScroll()) {
                        window.requestAnimationFrame(loadNextPage);
                    }
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

        function onInternalScroll() {
            if (mainScrollActive || completed) return;
            const remaining = scrollViewport.scrollHeight - scrollViewport.scrollTop - scrollViewport.clientHeight;
            if (remaining < 8) {
                if (isInternalFirst) activateMainScroll();
                loadNextPage();
            }
        }

        if (completed) {
            finish();
            return;
        }

        if (isInternalFirst) {
            // O lote inicial permanece em uma área própria; dez linhas podem
            // ultrapassar essa altura e tornar a barra interna utilizável.
            scrollViewport.addEventListener('scroll', onInternalScroll, { passive: true });
            if (!completed && totalPages > 1 && hasRoomToScroll()) activateMainScroll();
        } else {
            observer = 'IntersectionObserver' in window
                ? new IntersectionObserver((entries) => {
                    if (entries.some((entry) => entry.isIntersecting)) loadNextPage();
                }, { root: scrollViewport, rootMargin: '240px 0px', threshold: 0.01 })
                : null;
            sentinel.hidden = false;
            if (observer) observer.observe(sentinel);
            scrollViewport.addEventListener('scroll', onInternalScroll, { passive: true });
            updateStatus('', false);
            if (hasRoomToScroll()) window.requestAnimationFrame(loadNextPage);
        }
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
