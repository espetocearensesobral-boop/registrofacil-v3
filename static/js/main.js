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
// SIDEBAR: Toggle com Persistência de Estado
// ============================================================

// Chave do localStorage
const SIDEBAR_STATE_KEY = 'registrofacil_sidebar_collapsed';

/**
 * Inicializa a sidebar ao carregar a página
 */
function inicializarSidebar() {
    const sidebar = document.getElementById('sidebar');
    const wrapper = document.getElementById('wrapper');
    const pageContentWrapper = document.getElementById('page-content-wrapper');
    
    if (!sidebar || !wrapper) return;
    
    // Recuperar estado salvo
    const isCollapsed = localStorage.getItem(SIDEBAR_STATE_KEY) === 'true';
    
    // Aplicar estado SEM animação (já foi aplicado no head, mas garantimos)
    if (isCollapsed) {
        sidebar.classList.add('collapsed');
        wrapper.classList.add('toggled');
        if (pageContentWrapper) pageContentWrapper.style.marginLeft = '60px';
    } else {
        sidebar.classList.remove('collapsed');
        wrapper.classList.remove('toggled');
        if (pageContentWrapper) pageContentWrapper.style.marginLeft = '220px';
    }
    
    // Configurar botão de toggle (hamburger)
    const hamburger = document.querySelector('.hamburger-menu');
    if (hamburger) {
        hamburger.addEventListener('click', window.toggleSidebar);
    }
}

/**
 * Alterna o estado da sidebar
 */
window.toggleSidebar = function() {
    const sidebar = document.getElementById('sidebar');
    const wrapper = document.getElementById('wrapper');
    const pageContentWrapper = document.getElementById('page-content-wrapper');
    
    if (!sidebar || !wrapper) return;
    
    const isCollapsed = sidebar.classList.toggle('collapsed');
    wrapper.classList.toggle('toggled', isCollapsed);
    
    if (pageContentWrapper) {
        if (isCollapsed) {
            pageContentWrapper.style.marginLeft = '60px';
        } else {
            pageContentWrapper.style.marginLeft = '220px';
        }
    }
    
    // Salvar estado no localStorage
    localStorage.setItem(SIDEBAR_STATE_KEY, isCollapsed.toString());
    window.dispatchEvent(new Event('resize'));
    
    // NOVO: Ajustar estado da seção de perfil ao colapsar/expandir a sidebar
    const profileSectionToggle = document.getElementById('profile-section-toggle');
    const profileMenuItems = document.querySelector('.profile-menu-items');
    if (profileSectionToggle && profileMenuItems) {
        profileMenuItems.classList.add('collapsed');
        profileSectionToggle.classList.add('collapsed');
        profileSectionToggle.classList.remove('expanded');
    }
    
    console.log('Sidebar toggle: ' + (isCollapsed ? 'recolhida' : 'expandida'));
}

// INICIALIZAÇÃO da Sidebar
document.addEventListener('DOMContentLoaded', function() {
    inicializarSidebar();
    
    // Remover classe de estado inicial após aplicar (para não conflitar)
    document.documentElement.classList.remove('sidebar-collapsed-initial');
});

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

    // --- 2.3. Inicializa o Controle da Sidebar ---
    const initSidebarControl = () => {
        const sidebar = document.getElementById('sidebar');
        const wrapper = document.getElementById('wrapper');
        const pageContentWrapper = document.getElementById('page-content-wrapper');
        const hamburgerMenu = document.querySelector('.hamburger-menu');
        const sidebarCompanyLogo = document.getElementById('sidebar-company-logo');

        // NOVOS ELEMENTOS PARA SEÇÃO DO PERFIL RECOLHÍVEL
        const profileSectionToggle = document.getElementById('profile-section-toggle');
        const profileMenuItems = document.querySelector('.profile-menu-items');

        // Adição de logs para verificar se os elementos foram encontrados
        console.log("initSidebarControl: Verificando elementos da sidebar...");
        console.log("Sidebar elemento:", sidebar);
        console.log("Wrapper elemento:", wrapper);
        console.log("Page Content Wrapper elemento:", pageContentWrapper);
        console.log("Hamburger Menu elemento:", hamburgerMenu);
        console.log("Sidebar Company Logo elemento:", sidebarCompanyLogo);
        console.log("Profile Section Toggle elemento:", profileSectionToggle);
        console.log("Profile Menu Items elemento:", profileMenuItems);


        if (!sidebar || !wrapper || !pageContentWrapper || !hamburgerMenu || !profileSectionToggle || !profileMenuItems) {
            console.error('initSidebarControl: Um ou mais elementos essenciais da sidebar NÃO ENCONTRADOS. O controle da sidebar pode não funcionar corretamente.');
            return; // Interrompe a função se os elementos não forem encontrados
        }
        
        // Adiciona evento de clique no menu hambúrguer
        hamburgerMenu.addEventListener('click', window.toggleSidebar);
        
        // Adiciona evento de clique na logo da empresa para toggle da sidebar
        if (sidebarCompanyLogo) {
            sidebarCompanyLogo.style.cursor = 'pointer';
            sidebarCompanyLogo.addEventListener('click', (e) => {
                e.stopPropagation(); // Evita propagação para o hamburgerMenu
                window.toggleSidebar();
            });
            console.log('initSidebarControl: Evento de clique adicionado à logo da empresa.');
        }
        console.log('initSidebarControl: Listeners de clique adicionados para alternar a sidebar.');

        // Restaura o estado da sidebar (colapsada/expandida)
        // Por padrão (primeira visita), a sidebar inicia RECOLHIDA
        const savedSidebarState = localStorage.getItem(SIDEBAR_STATE_KEY);
        const isCollapsedInitially = savedSidebarState === null ? false : savedSidebarState === 'true';
        sidebar.classList.toggle('collapsed', isCollapsedInitially);
        wrapper.classList.toggle('toggled', isCollapsedInitially);
        pageContentWrapper.style.marginLeft = isCollapsedInitially ? '60px' : '220px';
        console.log(`initSidebarControl: Estado da sidebar restaurado para ${isCollapsedInitially ? 'recolhida' : 'expandida'}.`);

        // Lógica de estado inicial da seção de perfil
        // Força a seção de perfil a iniciar sempre recolhida.
        profileMenuItems.classList.add('collapsed');
        profileSectionToggle.classList.add('collapsed');
        profileSectionToggle.classList.remove('expanded'); // Garante que 'expanded' é removido
        console.log("initSidebarControl: Seção de perfil forçada a iniciar recolhida.");


        // Adiciona listener para o clique no botão "Opções"
        profileSectionToggle.addEventListener('click', (event) => {
            console.log("profileSectionToggle: Clique detectado. Alternando estado...");
            // Previne a propagação do evento para evitar interferências com outros listeners
            event.stopPropagation(); 
            
            const isCurrentlyCollapsed = profileMenuItems.classList.toggle('collapsed');
            profileSectionToggle.classList.toggle('collapsed', isCurrentlyCollapsed);
            profileSectionToggle.classList.toggle('expanded', !isCurrentlyCollapsed);
            
            // Rola a sidebar para o topo ou para o botão de toggle para garantir visibilidade
            if (!sidebar.classList.contains('collapsed')) {
                 sidebar.scrollTo({ top: sidebar.scrollHeight, behavior: 'smooth' });
            }
        });


        function handleResponsiveSidebar() {
            if (window.innerWidth <= 991) {
                // Mobile/tablet: sidebar é um drawer — NÃO adiciona .collapsed
                // (collapsed esconderia o texto mesmo com a sidebar aberta)
                // O controle visual é feito por transform via CSS + .mobile-open
                pageContentWrapper.style.marginLeft = '0';
                wrapper.classList.remove('toggled');

                // Garante que a sidebar não fica "aberta" ao redimensionar
                sidebar.classList.remove('mobile-open');
                document.getElementById('sidebar-overlay').classList.remove('active');
                document.body.style.overflow = '';

                // Recolhe seção de perfil
                profileMenuItems.classList.add('collapsed');
                profileSectionToggle.classList.add('collapsed');
                profileSectionToggle.classList.remove('expanded');
            } else {
                // Desktop: restaura estado salvo (collapsed ou expandido)
                const isSavedCollapsed = localStorage.getItem(SIDEBAR_STATE_KEY) === 'true';
                sidebar.classList.toggle('collapsed', isSavedCollapsed);
                sidebar.classList.remove('mobile-open'); // garante limpeza
                wrapper.classList.toggle('toggled', isSavedCollapsed);
                pageContentWrapper.style.marginLeft = isSavedCollapsed ? '60px' : '220px';

                // Recolhe seção de perfil
                profileMenuItems.classList.add('collapsed');
                profileSectionToggle.classList.add('collapsed');
                profileSectionToggle.classList.remove('expanded');
            }
        }
        window.addEventListener('resize', handleResponsiveSidebar);
        handleResponsiveSidebar(); // Executa ao carregar a página
        
        document.addEventListener('click', function(event) {
            // Mobile/tablet: fecha sidebar drawer ao clicar fora
            if (window.innerWidth <= 991 &&
                sidebar.classList.contains('mobile-open') &&
                !sidebar.contains(event.target) &&
                !event.target.closest('#mobile-menu-btn')) {
                window.closeMobileSidebar();
            }
        });
        console.log("initSidebarControl: Controle da sidebar inicializado.");
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
                // Se o item ativo está na seção de perfil, role para a seção de perfil
                const profileMenuItems = document.querySelector('.profile-menu-items');
                if (profileMenuItems && profileMenuItems.contains(activeItemFound)) {
                    const bottomSection = document.querySelector('.bottom-section');
                     if (bottomSection) {
                         bottomSection.scrollIntoView({ behavior: 'smooth', block: 'end' });
                         console.log("setActiveSidebarLinks: Rolando para o item ativo na seção de perfil.");
                     }
                } else if (menuSection && menuSection.contains(activeItemFound)) {
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


    // --- 2.8. Lógica de Pesquisa Global (Focada no Modal) ---
    function initializeGlobalSearchModal() {
        const globalSearchModalElement = document.getElementById('globalSearchModal');
        const modalGlobalSearchInput = document.getElementById('modal-global-search-input');
        const modalSearchResultsList = document.getElementById('modal-search-results-list');
        const modalSearchNoResults = document.getElementById('modal-search-no-results');

        let searchTimeout;

        if (!globalSearchModalElement || !modalGlobalSearchInput || !modalSearchResultsList || !modalSearchNoResults) {
            console.log("initializeGlobalSearchModal: Elementos do modal de pesquisa NÃO ENCONTRADOS, ignorando inicialização.");
            return;
        }
        console.log("initializeGlobalSearchModal: Elementos do modal de pesquisa encontrados. Inicializando lógica de pesquisa.");

        globalSearchModalElement.addEventListener('shown.bs.modal', function () {
            console.log("initializeGlobalSearchModal: Modal de pesquisa global aberto. Focando no input.");
            modalGlobalSearchInput.focus();
            modalSearchResultsList.innerHTML = '<div class="gs-empty" id="modal-search-no-results"><i class="bi bi-search"></i><p>Digite para buscar processos no sistema</p><p style="font-size:10px;margin-top:4px;opacity:.6;">Busca por titular, matrícula ou ID do processo</p></div>';
            modalGlobalSearchInput.value = '';
        });

        modalGlobalSearchInput.addEventListener('keydown', function(e) {
            const items = this._items || [];
            if (!items.length) return;
            let idx = (this._activeIdx !== undefined && this._activeIdx !== null) ? this._activeIdx : -1;

            if (e.key === 'ArrowDown') {
                e.preventDefault();
                e.stopPropagation();
                idx = Math.min(idx + 1, items.length - 1);
                items.forEach(el => el.classList.remove('gs-active'));
                if (items[idx]) {
                    items[idx].classList.add('gs-active');
                    items[idx].scrollIntoView({ block: 'nearest' });
                }
                this._activeIdx = idx;
            } else if (e.key === 'ArrowUp') {
                e.preventDefault();
                e.stopPropagation();
                idx = Math.max(idx - 1, 0);
                items.forEach(el => el.classList.remove('gs-active'));
                if (items[idx]) {
                    items[idx].classList.add('gs-active');
                    items[idx].scrollIntoView({ block: 'nearest' });
                }
                this._activeIdx = idx;
            } else if (e.key === 'Enter') {
                e.preventDefault();
                e.stopPropagation();
                const active = modalSearchResultsList.querySelector('.gs-item.gs-active');
                const target = active || items[0];
                if (target && target.dataset.url) {
                    const modalEl = document.getElementById('globalSearchModal');
                    const bsModal = bootstrap.Modal.getInstance(modalEl);
                    if (bsModal) {
                        modalEl.addEventListener('hidden.bs.modal', () => { window.location.href = target.dataset.url; }, { once: true });
                        bsModal.hide();
                    } else {
                        window.location.href = target.dataset.url;
                    }
                }
            }
        });
        modalGlobalSearchInput.addEventListener('input', function() {
            console.log("initializeGlobalSearchModal: Input de pesquisa do modal digitado.");
            clearTimeout(searchTimeout);
            const query = this.value.trim();

            if (query.length === 0) {
                modalSearchResultsList.innerHTML = '<div class="gs-empty" id="modal-search-no-results"><i class="bi bi-search"></i><p>Digite para buscar processos no sistema</p></div>';
                return;
            }

            modalSearchResultsList.innerHTML = '<div class="gs-loading"><div class="spinner-border spinner-border-sm me-2" style="width:14px;height:14px;" role="status"></div>Pesquisando...</div>';

            searchTimeout = setTimeout(async () => {
                console.log(`initializeGlobalSearchModal: Executando pesquisa para: '${query}'`);
                try {
                    const response = await fetch(`${FlaskRoutes.apiGlobalSearch}?q=${encodeURIComponent(query)}`);
                    const data = await response.json();

                    if (response.ok) {
                        if (data && data.length > 0) {
                            modalSearchResultsList.innerHTML = '<div class="gs-section-lbl"><i class="bi bi-folder2-open me-1"></i>Processos encontrados</div>';
                            let activeIdx = -1;
                            const items = [];
                            const modalEl = document.getElementById('globalSearchModal');
                            data.forEach(item => {
                                const listItem = document.createElement('a');
                                listItem.className = 'gs-item';
                                listItem.href = item.url;
                                listItem.dataset.url = item.url;

                                // Datas formatadas
                                const entradaLabel = item.data_entrada
                                    ? `<span title="Data de Entrada"><i class="bi bi-box-arrow-in-right" style="margin-right:2px;"></i>${item.data_entrada}</span>` : '';
                                const conclusaoLabel = item.data_conclusao
                                    ? `<span title="Data de Conclusão"><i class="bi bi-check2-circle" style="margin-right:2px;color:var(--color-success);"></i>${item.data_conclusao}</span>` : '';
                                const statusDot = item.hex_color
                                    ? `<span style="display:inline-block;width:7px;height:7px;border-radius:50%;background:${item.hex_color};flex-shrink:0;"></span>` : '';
                                const statusLabel = item.status_nome
                                    ? `${statusDot}<span>${item.status_nome}</span>` : '';
                                const matriculaLabel = item.matricula && item.matricula !== 'N/A'
                                    ? `<span><i class="bi bi-hash" style="margin-right:1px;"></i>${item.matricula}</span>` : '';
                                const numeroLabel = item.numero_processo
                                    ? `<span title="Número do Processo"><i class="bi bi-file-text" style="margin-right:2px;"></i>${item.numero_processo}</span>` : '';
                                const apresentanteLabel = item.apresentante
                                    ? `<span title="Apresentante"><i class="bi bi-person" style="margin-right:2px;"></i>${item.apresentante}</span>` : '';

                                const dot = '<span style="opacity:.35;margin:0 2px;">·</span>';
                                const metaParts = [matriculaLabel, numeroLabel, apresentanteLabel, entradaLabel, conclusaoLabel].filter(Boolean).join(dot);

                                listItem.innerHTML = `
                                    <div class="gs-item-icon"><i class="bi bi-file-earmark-text"></i></div>
                                    <div class="gs-item-text">
                                        <div class="gs-item-title">${item.title}</div>
                                        <div class="gs-item-sub" style="display:flex;align-items:center;gap:4px;flex-wrap:wrap;">
                                            ${metaParts}
                                            ${statusLabel ? dot + statusLabel : ''}
                                        </div>
                                    </div>
                                    <i class="bi bi-arrow-right-short gs-item-arrow"></i>`;

                                // Clique: fecha o modal antes de navegar
                                listItem.addEventListener('click', function(e) {
                                    e.preventDefault();
                                    const url = this.dataset.url;
                                    if (!url) return;
                                    const bsModal = bootstrap.Modal.getInstance(modalEl);
                                    if (bsModal) {
                                        modalEl.addEventListener('hidden.bs.modal', () => { window.location.href = url; }, { once: true });
                                        bsModal.hide();
                                    } else {
                                        window.location.href = url;
                                    }
                                });

                                items.push(listItem);
                                modalSearchResultsList.appendChild(listItem);
                            });
                            modalGlobalSearchInput._items = items;
                            modalGlobalSearchInput._activeIdx = -1;
                            console.log(`initializeGlobalSearchModal: ${data.length} resultados encontrados e exibidos.`);
                        } else {
                            modalSearchResultsList.innerHTML = `<div class="gs-empty"><i class="bi bi-inbox"></i><p>Nenhum resultado para "<strong>${query}</strong>"</p><p style="font-size:10px;margin-top:4px;opacity:.6;">Tente outros termos ou verifique a ortografia</p></div>`;
                            console.log("initializeGlobalSearchModal: Nenhum resultado encontrado.");
                        }
                    } else {
                        const errorData = data || {};
                        const errorMessage = errorData.message || `Erro do servidor: ${response.status} ${response.statusText}.`;
                        modalSearchResultsList.style.display = 'none';
                        modalSearchNoResults.style.display = 'block';
                        modalSearchNoResults.textContent = `Erro: ${errorMessage} Por favor, tente novamente.`;
                        console.error(`initializeGlobalSearchModal: Erro da API: ${errorMessage} (Status: ${response.status}).`);
                    }

                } catch (error) {
                    console.error('initializeGlobalSearchModal: Erro na requisição Fetch da pesquisa global:', error);
                    modalSearchResultsList.innerHTML = '<div class="gs-empty"><i class="bi bi-wifi-off"></i><p>Erro de rede. Verifique sua conexão.</p></div>';
                }
            }, 300);
        });  // end input listener
        console.log("initializeGlobalSearchModal: Lógica de pesquisa global inicializada.");
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
                'i': () => {
                    window.toggleSidebar();
                    return true;
                },
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
                    window.location.href = FlaskRoutes.atividadesHistorico;
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
                    const modalElement = document.querySelector('#aboutModal');
                    if (modalElement) {
                        const bsModal = new bootstrap.Modal(modalElement);
                        bsModal.show();
                    }
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
                    const profileSectionToggle = document.getElementById('profile-section-toggle');
                    if (profileSectionToggle) {
                        profileSectionToggle.click();
                    } else {
                        console.warn("Atalho para 'Opções' (Alt+O) acionado, mas o elemento de toggle não foi encontrado.");
                    }
                    return true;
                }
            };

            // Permite atalhos específicos mesmo em inputs
            const allowedInInputs = ['q', 'i', 'p', 'j', 'o'];
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