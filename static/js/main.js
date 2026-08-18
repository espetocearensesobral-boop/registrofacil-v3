// registrofacil/static/js/main.js

// === Importações de Módulos ===
import { showToast, togglePassword } from './utils/dom_helpers.js';
import { initializeProcessFormLogic } from './processos/form_logic.js';
import { initializeRecordLocking } from './processos/record_locking.js';


// === 1. Funções Auxiliares Comuns e Globais ===
// Exporte para o window para que os onclicks no HTML possam acessá-los
if (typeof window.showToast !== 'function') {
    window.showToast = showToast;
}
if (typeof window.togglePassword !== 'function') {
    window.togglePassword = togglePassword;
}

// ============================================================
// SIDEBAR: fixa e expandida no desktop. Todas as categorias, inclusive Administrador, usam o mesmo accordion.
function inicializarSidebar() {
    const sidebar = document.getElementById('sidebar');
    const wrapper = document.getElementById('wrapper');
    if (!sidebar || !wrapper) return;

    sidebar.classList.remove('collapsed', 'mobile-open');
    wrapper.classList.remove('toggled');
}

document.addEventListener('DOMContentLoaded', inicializarSidebar);

/**
 * Loading global não bloqueante. Sucesso e erro continuam sendo comunicados
 * pelo sistema atual de toasts/notificações.
 */
function obterGlobalLoading() {
    return document.getElementById('rf-global-loading');
}

window.showPageLoading = function(message = 'Carregando...') {
    const indicator = obterGlobalLoading();
    if (!indicator) return;
    const messageElement = indicator.querySelector('[data-rf-loading-message]');
    if (messageElement) messageElement.textContent = message;
    indicator.hidden = false;
    indicator.classList.add('is-visible');
};

window.hidePageLoading = function() {
    const indicator = obterGlobalLoading();
    if (!indicator) return;
    indicator.classList.remove('is-visible');
    indicator.hidden = true;
};

function inicializarLoadingNavegacao() {
    document.addEventListener('click', function(event) {
        const trigger = event.target.closest('a[href], [data-href]');
        if (!trigger || event.defaultPrevented) return;
        if (event.button !== undefined && event.button !== 0) return;
        if (event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) return;
        if (trigger.matches('[data-bs-toggle], [data-bs-dismiss]')) return;
        if (trigger.getAttribute('target') === '_blank' || trigger.hasAttribute('download')) return;

        const href = trigger.getAttribute('href') || trigger.dataset.href || '';
        if (!href || href === '#' || href.startsWith('javascript:')) return;
        if (href.startsWith('mailto:') || href.startsWith('tel:')) return;

        const isDownloadOrDocument = /export|imprimir|gerar_pdf|\.pdf(?:$|\?)/i.test(href);
        window.showPageLoading(trigger.dataset.loadingText || (isDownloadOrDocument ? 'Preparando arquivo...' : 'Abrindo...'));
        if (isDownloadOrDocument) window.setTimeout(window.hidePageLoading, 1400);
    });
}

document.addEventListener('DOMContentLoaded', inicializarLoadingNavegacao);

/**
 * Estado visual comum para ações de envio: confirma o clique, evita duplo envio
 * e preserva o texto específico de cada ação sem alterar o fluxo do backend.
 */
function inicializarEstadosDeEnvio() {
    document.querySelectorAll('form').forEach(form => {
        const declaredSubmitState = form.hasAttribute('data-rf-submit-state');
        const declaredSubmitButton = form.querySelector('button[type="submit"][data-loading-text]');
        if (!declaredSubmitState && !declaredSubmitButton) return;
        if (form.dataset.rfSubmitStateReady === 'true') return;
        form.dataset.rfSubmitStateReady = 'true';
        form.addEventListener('submit', function(event) {
            // Handlers AJAX existentes exibem seus próprios toasts e loading; não duplicar.
            if (event.defaultPrevented) return;
            const submitButton = event.submitter || this.querySelector('button[type="submit"]:not([data-no-submit-state])');
            if (!submitButton || submitButton.dataset.rfSubmitting === 'true') return;
            submitButton.dataset.rfSubmitting = 'true';
            submitButton.dataset.rfOriginalHtml = submitButton.innerHTML;
            const loadingText = submitButton.dataset.loadingText || this.dataset.submitLabel || 'Processando...';
            window.showPageLoading(loadingText);
            submitButton.disabled = true;
            submitButton.setAttribute('aria-busy', 'true');
            submitButton.innerHTML = `<span class="spinner-border spinner-border-sm me-1" aria-hidden="true"></span>${loadingText}`;
            this.setAttribute('aria-busy', 'true');
        });
    });
}

document.addEventListener('DOMContentLoaded', inicializarEstadosDeEnvio);

/**
 * Ativa o item de menu clicado na sidebar e lida com a navegação/abertura de modais.
 * @param {HTMLElement} element - O elemento .menu-item clicado.
 */
window.setActive = function(element) {
    console.log("setActive: Item de menu clicado.", element);
    const menuItems = document.querySelectorAll('.menu-item');
    
    menuItems.forEach(item => item.classList.remove('active'));
    
    element.classList.add('active');

    // NOVO: Rola a sidebar para o item ativo, se encontrado
    const menuSection = document.querySelector('.menu-section');
    if (menuSection && menuSection.contains(element)) { // Certifica que o elemento está dentro da seção rolável
        // Calcula a posição relativa do item dentro da seção de rolagem
        const elementTop = element.offsetTop; // Posição do topo do elemento em relação ao seu offsetParent (menuSection)
        const elementHeight = element.offsetHeight;
        const sectionScrollTop = menuSection.scrollTop;
        const sectionHeight = menuSection.offsetHeight;

        // Se o elemento está acima da visão atual ou abaixo da visão atual
        if (elementTop < sectionScrollTop || (elementTop + elementHeight) > (sectionScrollTop + sectionHeight)) {
            // Calcula a nova posição de rolagem para centralizar o elemento
            const newScrollTop = elementTop - (sectionHeight / 2) + (elementHeight / 2);
            menuSection.scrollTo({
                top: newScrollTop,
                behavior: 'smooth'
            });
            console.log("setActive: Rolando sidebar para o item ativo.");
        }
    }
    
    const isModalTrigger = element.hasAttribute('data-bs-toggle') && element.getAttribute('data-bs-toggle') === 'modal';
    
    if (!isModalTrigger) {
        const href = element.dataset.href;
        if (href && href !== '#') {
            window.location.href = href;
            console.log(`setActive: Redirecionando para: ${href}`);
        } else {
            console.warn("setActive: Item de menu não tem href válido para navegação.", element);
        }
    } else {
        const targetModalId = element.getAttribute('data-bs-target');
        if (targetModalId) {
            const modalElement = document.querySelector(targetModalId);
            if (modalElement) {
                console.log(`setActive: Acionando modal: ${targetModalId}`);
                modalElement.addEventListener('hidden.bs.modal', () => {
                    element.classList.remove('active');
                    setActiveSidebarLinks();
                }, { once: true });
            } else {
                console.error(`setActive: Elemento modal com ID '${targetModalId}' NÃO ENCONTRADO.`);
            }
        } else {
            console.warn("setActive: Item de menu modal não tem 'data-bs-target'.", element);
        }
    }
}

// =============================================================
// === INICIALIZAÇÕES PRINCIPAIS (APÓS DOMContentLoaded) ===
// =============================================================

document.addEventListener('DOMContentLoaded', function() {
    console.log("main.js: DOMContentLoaded disparado. Iniciando inicializações...");

    if (typeof FlaskRoutes === 'undefined') {
        console.error("main.js: Objeto FlaskRoutes não encontrado! Funções de rota não estarão disponíveis.");
        return;
    }

    // --- 2.1. Inicializa Toasts de Mensagens Flash ---
    function initializeFlashToasts() {
        const flashToasts = document.querySelectorAll('.toast');
        if (flashToasts.length === 0) {
            console.log("initializeFlashToasts: Nenhum toast de mensagem flash encontrado.");
            return;
        }
        flashToasts.forEach(toastEl => {
            const bsToast = new bootstrap.Toast(toastEl);
            bsToast.show();
            toastEl.addEventListener('hidden.bs.toast', () => toastEl.remove());
        });
        console.log("initializeFlashToasts: Toasts de mensagens flash inicializados.");
    }
    initializeFlashToasts();

    // --- 2.3. Inicializa a sidebar fixa e a navegação sempre aberta ---
    const initSidebarControl = () => {
        const sidebar = document.getElementById('sidebar');
        const wrapper = document.getElementById('wrapper');
        const pageContentWrapper = document.getElementById('page-content-wrapper');
        if (!sidebar || !wrapper || !pageContentWrapper) return;

        sidebar.classList.remove('collapsed');
        wrapper.classList.remove('toggled');

        const handleResponsiveSidebar = () => {
            sidebar.classList.remove('collapsed');
            wrapper.classList.remove('toggled');
            if (window.innerWidth > 991) {
                sidebar.classList.remove('mobile-open');
                document.getElementById('sidebar-overlay')?.classList.remove('active');
                document.body.style.overflow = '';
            }
        };
        window.addEventListener('resize', handleResponsiveSidebar);
        handleResponsiveSidebar();

        document.addEventListener('click', event => {
            if (window.innerWidth <= 991 && sidebar.classList.contains('mobile-open') &&
                !sidebar.contains(event.target) && !event.target.closest('#mobile-menu-btn')) {
                window.closeMobileSidebar?.();
            }
        });
    };
    initSidebarControl();

    // --- 2.4. Ativação de Links da Sidebar (para o item de menu selecionado) ---
    const setActiveSidebarLinks = () => {
        const currentPath = window.location.pathname;
        const menuItems = document.querySelectorAll('.menu-item[data-href], .menu-item[data-bs-toggle="modal"]'); 
        
        if (menuItems.length === 0) {
            console.warn("setActiveSidebarLinks: Nenhum '.menu-item' encontrado. Pulando ativação de links.");
            return;
        }

        menuItems.forEach(item => item.classList.remove('active'));

        let activeItemFound = null; // Para guardar o item ativo

        menuItems.forEach(item => {
            const linkHref = item.dataset.href;
            const isModal = item.hasAttribute('data-bs-toggle') && item.getAttribute('data-bs-toggle') === 'modal';

            const cleanLinkHref = linkHref ? linkHref.split('?')[0].split('#')[0] : '';
            const cleanCurrentPath = currentPath.split('?')[0].split('#')[0];

            let isActiveCandidate = false;

            if (!isModal && cleanLinkHref) {
                if (cleanLinkHref === cleanCurrentPath) {
                    isActiveCandidate = true;
                }
                else if (cleanCurrentPath.startsWith(FlaskRoutes.processosVisualizarBase) ||
                         cleanCurrentPath.startsWith(FlaskRoutes.processosEditarBase)) {
                    if (cleanLinkHref === FlaskRoutes.processosTodos) {
                        isActiveCandidate = true; 
                    }
                }
                else if (cleanCurrentPath.startsWith(FlaskRoutes.adminEditUserBase)) {
                    // Para o link "Meu Perfil", verifica se o ID na URL é o mesmo do usuário logado
                    const meuPerfilItem = document.querySelector('.menu-item[data-accesskey="m"]');
                    if (meuPerfilItem && item === meuPerfilItem) {
                        const loggedInUserId = meuPerfilItem.dataset.href ? meuPerfilItem.dataset.href.split('/').pop() : null;
                        const currentPathUserId = cleanCurrentPath.split('/').pop();
                        if (loggedInUserId && currentPathUserId && loggedInUserId === currentPathUserId) {
                             isActiveCandidate = true;
                        }
                    } else if (cleanLinkHref === FlaskRoutes.adminUsersList && cleanCurrentPath.startsWith(FlaskRoutes.adminUsersList)) {
                        isActiveCandidate = true;
                    }
                }
                else if (cleanCurrentPath.startsWith('/configuracoes') && cleanLinkHref === FlaskRoutes.configuracoesIndex) {
                    isActiveCandidate = true; 
                }
                else if (cleanCurrentPath.startsWith('/empresa') && cleanLinkHref === FlaskRoutes.empresaIndex) {
                    isActiveCandidate = true; 
                }
                else if (cleanCurrentPath.startsWith('/backup') && cleanLinkHref === FlaskRoutes.backupIndex) {
                    isActiveCandidate = true; 
                }
            } else if (isModal && cleanLinkHref === cleanCurrentPath) { // Para modais que podem ser ativados por rota direta
                isActiveCandidate = true;
            }

            if (isActiveCandidate) {
                item.classList.add('active');
                activeItemFound = item;
                console.log(`setActiveSidebarLinks: Link ativo definido para: '${linkHref}'`);
            }
        });

        // Rola a sidebar para o item ativo, se encontrado
        if (activeItemFound) {
            // Pequeno delay para garantir que a sidebar já se ajustou (se expandindo) antes de rolar
            setTimeout(() => {
                const menuSection = document.querySelector('.menu-section');
                if (menuSection && menuSection.contains(activeItemFound)) {
                    // Calcula a posição do item para centralizá-lo na área visível
                    const itemOffsetTop = activeItemFound.offsetTop;
                    const itemHeight = activeItemFound.offsetHeight;
                    const sectionHeight = menuSection.offsetHeight;
                    
                    // Rola para centralizar o item na visão
                    const newScrollTop = itemOffsetTop - (sectionHeight / 2) + (itemHeight / 2);
                    menuSection.scrollTo({
                        top: newScrollTop,
                        behavior: 'smooth'
                    });
                    console.log("setActiveSidebarLinks: Sidebar rolada para o item ativo na seção principal.");
                }
            }, 100); // 100ms de delay
        }


        const globalSearchBtnNavbar = document.querySelector('.navbar .btn[data-bs-target="#globalSearchModal"]');
        if (globalSearchBtnNavbar) {
            globalSearchBtnNavbar.addEventListener('click', () => {
                const searchMenuItemSidebar = document.querySelector('.menu-item[data-bs-target="#globalSearchModal"]');
                if (searchMenuItemSidebar) {
                    window.setActive(searchMenuItemSidebar); 
                }
            });
        }
        console.log("setActiveSidebarLinks: Ativação de links da sidebar concluída.");
    };
    setActiveSidebarLinks();


    // --- 2.5. Inicialização de Tooltips do Bootstrap (em toda a aplicação) ---
    const initBootstrapTooltips = () => {
        const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
        
        if (tooltipTriggerList.length === 0) {
            console.log('initBootstrapTooltips: Nenhum tooltip do Bootstrap encontrado para inicializar.');
            return;
        }
        
        tooltipTriggerList.map(tooltipTriggerEl => {
            new bootstrap.Tooltip(tooltipTriggerEl);
        });
        console.log('initBootstrapTooltips: Tooltips do Bootstrap inicializados.');
    };
    initBootstrapTooltips();


    // --- 2.6. Lógica do Modal de Confirmação de Exclusão (Global) ---
    function initializeConfirmDeleteModal() {
        const confirmDeleteModal = document.getElementById('confirmDeleteModal');
        if (!confirmDeleteModal) {
            console.log('initializeConfirmDeleteModal: Modal de exclusão não encontrado, ignorando inicialização.');
            return;
        }
        confirmDeleteModal.addEventListener('show.bs.modal', function (event) {
            const button = event.relatedTarget;
            if (button) {
                const processId = button.getAttribute('data-id');
                const modalForm = this.querySelector('#deleteForm');
                if (modalForm) {
                    const deleteProcessIdInput = modalForm.querySelector('#deleteProcessId');
                    if (deleteProcessIdInput) {
                        deleteProcessIdInput.value = processId;
                        // Define a action do formulário para a rota de exclusão
                        if (FlaskRoutes && FlaskRoutes.processosExcluir) {
                            modalForm.action = FlaskRoutes.processosExcluir;
                        }
                        console.log(`initializeConfirmDeleteModal: ID de processo ${processId} setado no modal.`);
                    } else {
                        console.error("initializeConfirmDeleteModal: Campo '#deleteProcessId' NÃO ENCONTRADO no formulário do modal.");
                    }
                } else {
                    console.error("initializeConfirmDeleteModal: Formulário '#deleteForm' NÃO ENCONTRADO no modal de exclusão.");
                }
            } else {
                console.warn("initializeConfirmDeleteModal: Evento show.bs.modal disparado sem um 'relatedTarget' (botão que o acionou).");
            }
        });
        console.log("initializeConfirmDeleteModal: Lógica do modal de confirmação de exclusão inicializada.");
    }
    initializeConfirmDeleteModal();


    // --- 2.7. Validação de Datas (para campos como data_inicio, data_fim, prazo_final) ---
    function initializeDateValidation() {
        const dataInicio = document.getElementById('data_inicio');
        const dataFim = document.getElementById('data_fim');
        if (dataInicio && dataFim) {
            dataInicio.addEventListener('change', function() {
                if (this.value && dataFim.value && this.value > dataFim.value) {
                    showToast('warning', 'Data de início não pode ser posterior à data de fim.');
                    this.value = '';
                    this.focus();
                }
            });
            dataFim.addEventListener('change', function() {
                if (dataInicio.value && this.value && new Date(dataInicio.value) > new Date(this.value)) {
                    showToast('warning', 'Data de fim não pode ser anterior à data de início.');
                    this.value = '';
                    this.focus();
                }
            });
            console.log("initializeDateValidation: Campos de data (data_inicio, data_fim) inicializados.");
        } else {
            console.log("initializeDateValidation: Campos de data (data_inicio, data_fim) NÃO ENCONTRADOS.");
        }

        const prazoFinalField = document.getElementById('prazo_final');
        if (prazoFinalField) {
            // Datas retroativas são permitidas (ex: lançamento de prazos já vencidos)
            // Removido: prazoFinalField.min = hoje
            console.log("initializeDateValidation: Campo prazo_final encontrado (sem restrição de data mínima).");
        } else {
            console.log("initializeDateValidation: Campo prazo_final NÃO ENCONTRADO.");
        }
    }
    initializeDateValidation();


    // --- 2.8. Lógica da Busca Inteligente ---
    function initializeGlobalSearchModal() {
        const modal = document.getElementById('globalSearchModal');
        const input = document.getElementById('modal-global-search-input');
        const clear = document.getElementById('modal-global-search-clear');
        const results = document.getElementById('modal-search-results-list');
        const summary = document.getElementById('modal-search-summary');
        const pagination = document.getElementById('modal-search-pagination');
        if (!modal || !input || !clear || !results || !summary || !pagination) return;

        let timer;
        let page = 1;
        const escapeHtml = value => String(value ?? '').replace(/[&<>\'"]/g, char => ({'&':'&amp;', '<':'&lt;', '>':'&gt;', "'":'&#39;', '"':'&quot;'}[char]));
        const formatDate = value => value ? new Date(String(value).replace(' ', 'T')).toLocaleDateString('pt-BR') : '—';


        function render(data) {
            summary.textContent = `${data.total || 0} processo(s) encontrado(s)`;
            if (!data.processos || !data.processos.length) {
                results.innerHTML = '<div class="gs-empty"><i class="bi bi-inbox"></i><p>Nenhum processo encontrado.</p><p class="rf-search-hint">Digite outro nome, telefone, matrícula, ID ou processo.</p></div>';
                pagination.innerHTML = '';
                return;
            }
            results.innerHTML = data.processos.map(item => `
                <article class="rf-process-report-row">
                    <div class="rf-process-report-main">
                        <div class="rf-process-report-title"><strong>${escapeHtml(item.titular || 'Titular não informado')}</strong><span class="rf-process-report-status" style="--status-color:${escapeHtml(item.status_hex || '#777')}" >${escapeHtml(item.status_nome || 'Sem status')}</span></div>
                        <div class="rf-process-report-meta"><span><i class="bi bi-tag"></i>${escapeHtml(item.tipo_nome || 'Sem tipo')}</span><span><i class="bi bi-card-text"></i>Matrícula: ${escapeHtml(item.matricula || 'Não informada')}</span><span><i class="bi bi-calendar3"></i>${formatDate(item.data_entrada)}</span>${item.apresentante ? `<span><i class="bi bi-person"></i>${escapeHtml(item.apresentante)}</span>` : ''}</div>
                    </div>
                    <div class="rf-process-report-actions" aria-label="Ações do processo"><a class="nav-btn nav-btn-secondary rf-search-action" href="${item.visualizar_url}" aria-label="Visualizar processo" title="Visualizar processo"><i class="bi bi-eye" aria-hidden="true"></i></a><a class="nav-btn nav-btn-secondary rf-search-action" target="_blank" rel="noopener" href="${item.imprimir_url}" aria-label="Imprimir processo" title="Imprimir processo"><i class="bi bi-printer" aria-hidden="true"></i></a><a class="nav-btn nav-btn-primary rf-search-action" href="${item.baixar_url}" aria-label="Baixar PDF do processo" title="Baixar PDF"><i class="bi bi-file-earmark-pdf" aria-hidden="true"></i></a></div>
                </article>`).join('');
            pagination.innerHTML = (data.total_paginas || 1) > 1 ? `<button type="button" class="nav-btn nav-btn-secondary" ${data.pagina <= 1 ? 'disabled' : ''} data-page="${data.pagina - 1}"><i class="bi bi-chevron-left"></i></button><span>Página ${data.pagina} de ${data.total_paginas}</span><button type="button" class="nav-btn nav-btn-secondary" ${data.pagina >= data.total_paginas ? 'disabled' : ''} data-page="${data.pagina + 1}"><i class="bi bi-chevron-right"></i></button>` : '';
        }

        function showIdleState() {
            results.innerHTML = '<div class="gs-empty"><i class="bi bi-search" aria-hidden="true"></i><p>Digite uma pesquisa para começar.</p><p class="rf-search-hint">A busca será realizada automaticamente por nome, telefone, matrícula, ID ou processo.</p></div>';
            summary.textContent = 'Digite uma pesquisa para consultar processos.';
            pagination.innerHTML = '';
        }
        async function load() {
            const query = input.value.trim();
            if (!query) {
                showIdleState();
                return;
            }
            const params = new URLSearchParams({ q: query, pagina: page, por_pagina: 25 });
            results.innerHTML = '<div class="gs-loading"><span class="spinner-border spinner-border-sm me-2" aria-hidden="true"></span>Pesquisando...</div>';
            try {
                const response = await fetch(`${FlaskRoutes.apiSmartSearch}?${params}`, { credentials: 'same-origin' });
                const data = await response.json();
                if (!response.ok || !data.success) throw new Error(data.message || 'Falha na busca');
                render(data);
            } catch (error) {
                results.innerHTML = '<div class="gs-empty"><i class="bi bi-wifi-off"></i><p>Não foi possível realizar a busca.</p></div>';
                summary.textContent = 'Erro ao carregar resultados';
                console.error('Busca inteligente:', error);
            }
        }

        function schedule() { page = 1; clearTimeout(timer); timer = setTimeout(load, 250); }
        modal.addEventListener('shown.bs.modal', () => { input.focus(); showIdleState(); });
        input.addEventListener('input', schedule);
        clear.addEventListener('click', () => { input.value = ''; page = 1; showIdleState(); input.focus(); });
        pagination.addEventListener('click', event => { const button = event.target.closest('[data-page]'); if (button && !button.disabled) { page = Number(button.dataset.page); load(); } });
        modal.addEventListener('hidden.bs.modal', () => { input.value = ''; page = 1; showIdleState(); });
    }
    initializeGlobalSearchModal();


    // --- 2.9. Lógica de Formulários de Processo (Cadastro/Edição) ---
    if (document.getElementById('form-processo')) {
        initializeProcessFormLogic(FlaskRoutes);
        console.log("initializeProcessFormLogic: Lógica de formulário de processo inicializada.");
    } else {
        console.log("initializeProcessFormLogic: Formulário de processo NÃO ENCONTRADO. Pulando inicialização.");
    }


    // --- 2.10. Lógica de Bloqueio de Edição para Processos ---
    const LOCK_TIMEOUT_MINUTES_JS = document.body.dataset.lockTimeoutMinutes ? parseInt(document.body.dataset.lockTimeoutMinutes) : 15;
    initializeRecordLocking(FlaskRoutes, LOCK_TIMEOUT_MINUTES_JS);
    console.log("initializeRecordLocking: Lógica de bloqueio de registro inicializada.");


    // ─── UPPERCASE GLOBAL (exceto observações/textarea/email/senha/data/arquivo) ───
    (function aplicarUppercaseGlobal() {
        const UPPER_SELECTOR = [
            'input:not([type="email"])',
            'input:not([type="password"])',
            'input:not([name="csrf_token"])',
            'input:not([type="date"])',
            'input:not([type="file"])',
            'input:not([type="checkbox"])',
            'input:not([type="radio"])',
            'input:not([type="number"])',
            'input:not([type="hidden"])'
        ];
        // Seleciona inputs que não são nenhum dos tipos excluídos
        const inputs = document.querySelectorAll(
            'input:not([type="email"]):not([type="password"]):not([name="csrf_token"])' +
            ':not([type="date"]):not([type="file"]):not([type="checkbox"]):not([type="radio"])' +
            ':not([type="number"]):not([type="hidden"]):not([data-no-upper]):not([class*="no-upper"])'
        );
        inputs.forEach(function(inp) {
            // Não aplicar em campos de observação ou que tenham a classe/atributo de exclusão
            const name = (inp.name || '').toLowerCase();
            const id = (inp.id || '').toLowerCase();
            const cls = (inp.className || '').toLowerCase();
            if (name.includes('obs') || id.includes('obs') || cls.includes('no-upper') || 
                name.includes('senha') || name.includes('password') || name.includes('email')) return;

            // Aplicar uppercase ao valor já existente
            if (inp.value && inp.type !== 'email') {
                inp.value = inp.value.toUpperCase();
            }
            // Aplicar em tempo real durante digitação
            inp.addEventListener('input', function() {
                if (this.type === 'email') return;
                const pos = this.selectionStart;
                this.value = this.value.toUpperCase();
                try { this.setSelectionRange(pos, pos); } catch(e) {}
            });
        });

        // Selects — aplicar uppercase no texto visível (via CSS é mais correto)
        document.querySelectorAll('select:not([data-no-upper])').forEach(function(sel) {
            sel.style.textTransform = 'uppercase';
        });
    })();

    // ─── ENTER → PRÓXIMO CAMPO (Tab) ────────────────────────────────
    (function aplicarEnterTabGlobal() {
        const TABBABLE = 'input:not([type="hidden"]):not([type="file"]):not([disabled]), select:not([disabled]), textarea:not([disabled]), button:not([disabled])';
        document.addEventListener('keydown', function(e) {
            if (e.key !== 'Enter') return;
            const tag = e.target.tagName;
            // Não interceptar em textarea, botões de submit, select com multiple
            if (tag === 'TEXTAREA') return;
            if (tag === 'BUTTON') return;
            if (tag === 'SELECT') return; // permitir seleção normal
            if (e.target.type === 'submit') return;

            // Verificar se o target é um input dentro de um formulário
            if (tag !== 'INPUT' && tag !== 'SELECT') return;

            e.preventDefault();
            // Buscar todos os elementos tabbable no documento
            const allTabbable = Array.from(document.querySelectorAll(TABBABLE)).filter(function(el) {
                return !el.disabled && el.offsetParent !== null && el.tabIndex >= 0;
            });
            const idx = allTabbable.indexOf(e.target);
            if (idx >= 0 && idx < allTabbable.length - 1) {
                allTabbable[idx + 1].focus();
            } else if (idx === allTabbable.length - 1) {
                // Último campo — tentar submeter o formulário
                const form = e.target.closest('form');
                if (form) {
                    const submitBtn = form.querySelector('[type="submit"]');
                    if (submitBtn) submitBtn.click();
                }
            }
        }, true);
    })();

    // --- 2.11. Lógica de Atalhos de Teclado ---
    document.addEventListener('keydown', function(e) {
        if (e.altKey) {
            const activeElementTag = document.activeElement ? document.activeElement.tagName : '';
            const isInputOrTextarea = (activeElementTag === 'INPUT' || activeElementTag === 'TEXTAREA' || activeElementTag === 'SELECT');

            const key = e.key.toLowerCase();
            let handledByShortcut = false;

            const shortcutActions = {
                'd': () => {
                    window.location.href = FlaskRoutes.dashboard;
                    return true;
                },
                'q': () => {
                    const modalElement = document.querySelector('#globalSearchModal');
                    if (modalElement) {
                        const bsModal = new bootstrap.Modal(modalElement);
                        bsModal.show();
                    }
                    return true;
                },
                't': () => {
                    window.location.href = FlaskRoutes.processosTodos;
                    return true;
                },
                'n': () => {
                    window.location.href = FlaskRoutes.processosNovo;
                    return true;
                },
                'h': () => {
                    window.location.href = FlaskRoutes.processosHoje;
                    return true;
                },
                'e': () => {
                    window.location.href = FlaskRoutes.processosPendentes;
                    return true;
                },
                'f': () => {
                    window.location.href = FlaskRoutes.processosVinculados;
                    return true;
                },
                'a': () => {
                    window.location.href = FlaskRoutes.configuracoesIndex + '?tab=atividades';
                    return true;
                },
                's': () => {
                    window.location.href = FlaskRoutes.configuracoesIndex;
                    return true;
                },
                'u': () => {
                    // Adicionar uma verificação de role, se necessário.
                    // Por enquanto, apenas redireciona se o link estiver disponível
                    const userLink = document.querySelector('.menu-item[data-accesskey="u"]');
                    if (userLink) {
                        window.location.href = FlaskRoutes.adminUsersList;
                    } else {
                        console.warn("Atalho para Usuários (Alt+U) acionado, mas link não disponível (talvez permissão).");
                    }
                    return true;
                },
                'b': () => {
                    window.location.href = FlaskRoutes.backupIndex;
                    return true;
                },
                'r': () => {
                    window.location.href = FlaskRoutes.empresaIndex;
                    return true;
                },
                'm': () => {
                    window.location.href = FlaskRoutes.perfilIndex;
                    return true;
                },
                'p': () => {
                    window.location.href = FlaskRoutes.configuracoesIndex + '?tab=sobre';
                    return true;
                },
                'j': () => {
                    const modalElement = document.querySelector('#shortcutsModal');
                    if (modalElement) {
                        const bsModal = new bootstrap.Modal(modalElement);
                        bsModal.show();
                    }
                    return true;
                },
                'x': () => {
                    window.location.href = FlaskRoutes.authLogout;
                    return true;
                },
                'o': () => {
                    const administratorLink = document.querySelector('.menu-item[data-accesskey="u"]');
                    if (administratorLink) {
                        administratorLink.focus({ preventScroll: true });
                        administratorLink.classList.add('active');
                    } else {
                        console.warn("Atalho Alt+O acionado, mas o acesso administrativo não está disponível.");
                    }
                    return true;
                }
            };

            // Permite atalhos específicos mesmo em inputs
            const allowedInInputs = ['q', 'p', 'j', 'o'];
            if (isInputOrTextarea && !allowedInInputs.includes(key)) {
                 return;
            }
            
            if (shortcutActions[key]) {
                e.preventDefault();
                handledByShortcut = shortcutActions[key]();
            }

            if (!handledByShortcut) {
                console.log(`Atalho Alt+${e.key.toUpperCase()} acionado, mas não tratado ou sem ação definida.`);
            }
        }
    });
    console.log("Atalhos de teclado inicializados.");

}); // Fim do evento DOMContentLoaded