/* Preferências visuais por usuário: três temas institucionais + seleção da sidebar. */

let temaSelecionado = null;
let corSidebarSelecionada = null;
let temaOriginal = null;
let corSidebarOriginal = null;

function aplicarPreferenciasVisuais(tema, corSidebar) {
    if (tema) {
        document.body.setAttribute('data-cor', tema);
        temaSelecionado = tema;
        const badge = document.getElementById('paleta-atual-badge');
        if (badge) badge.style.backgroundColor = 'var(--color-primary)';
    }
    if (corSidebar) {
        corSidebarSelecionada = corSidebar;
        document.documentElement.style.setProperty('--sidebar-selection-color', corSidebar);
        const badge = document.getElementById('sidebar-cor-atual-badge');
        if (badge) badge.style.backgroundColor = corSidebar;
    }
}

function selecionarTema(tema) {
    temaSelecionado = tema;
    document.querySelectorAll('.theme-choice').forEach((choice) => {
        choice.classList.toggle('selected', choice.dataset.theme === tema);
    });
    aplicarPreferenciasVisuais(tema, corSidebarSelecionada);
}

function selecionarCorSidebar(cor) {
    corSidebarSelecionada = cor;
    document.querySelectorAll('.sidebar-color-choice').forEach((choice) => {
        choice.classList.toggle('selected', choice.dataset.sidebarColor === cor);
    });
    aplicarPreferenciasVisuais(temaSelecionado, cor);
}

async function carregarPreferenciasVisuais() {
    try {
        const response = await fetch('/perfil/tema');
        if (!response.ok) return;
        const data = await response.json();
        temaOriginal = data.tema_cor || 'paleta-01';
        corSidebarOriginal = data.sidebar_selection_color || '#1B4368';
        temaSelecionado = temaOriginal;
        corSidebarSelecionada = corSidebarOriginal;
        aplicarPreferenciasVisuais(temaOriginal, corSidebarOriginal);
    } catch (error) {
        console.error('Erro ao carregar preferências visuais:', error);
    }
}

async function salvarAparencia() {
    const button = document.getElementById('btn-salvar-aparencia');
    if (!temaSelecionado || !corSidebarSelecionada || !button) return;
    const originalHtml = button.innerHTML;
    button.disabled = true;
    button.innerHTML = '<span class="spinner-border spinner-border-sm me-2"></span>Salvando...';
    try {
        const csrf = document.querySelector('[name="csrf_token"]')?.value || '';
        const headers = {'Content-Type': 'application/json', 'X-CSRFToken': csrf};
        const temaResponse = await fetch('/perfil/salvar-tema', {
            method: 'POST', headers, body: JSON.stringify({tema: temaSelecionado})
        });
        const temaData = await temaResponse.json();
        if (!temaResponse.ok || !temaData.success) throw new Error(temaData.message || 'Não foi possível salvar o tema.');

        const sidebarResponse = await fetch('/perfil/salvar-sidebar-cor', {
            method: 'POST', headers, body: JSON.stringify({sidebar_selection_color: corSidebarSelecionada})
        });
        const sidebarData = await sidebarResponse.json();
        if (!sidebarResponse.ok || !sidebarData.success) throw new Error(sidebarData.message || 'Não foi possível salvar a cor da sidebar.');

        temaOriginal = temaSelecionado;
        corSidebarOriginal = corSidebarSelecionada;
        if (typeof window.showToast === 'function') {
            window.showToast({type: 'success', title: 'Aparência salva', message: 'Tema e seleção da sidebar atualizados.'});
        }
        const modal = bootstrap.Modal.getInstance(document.getElementById('modalPaletas'));
        if (modal) modal.hide();
    } catch (error) {
        if (typeof window.showToast === 'function') {
            window.showToast({type: 'danger', title: 'Erro ao salvar aparência', message: error.message});
        } else {
            alert(error.message);
        }
        aplicarPreferenciasVisuais(temaOriginal, corSidebarOriginal);
    } finally {
        button.disabled = false;
        button.innerHTML = originalHtml;
    }
}

document.addEventListener('DOMContentLoaded', function() {
    carregarPreferenciasVisuais();
    document.querySelectorAll('.theme-choice').forEach((choice) => {
        choice.addEventListener('click', () => selecionarTema(choice.dataset.theme));
    });
    document.querySelectorAll('.sidebar-color-choice').forEach((choice) => {
        choice.addEventListener('click', () => selecionarCorSidebar(choice.dataset.sidebarColor));
    });
    const saveButton = document.getElementById('btn-salvar-aparencia');
    if (saveButton) saveButton.addEventListener('click', salvarAparencia);
});
