let temaSelecionado = null;
let temaOriginal = null;

function obterNomeTema(tema) {
    const choice = document.querySelector(`.theme-choice[data-palette="${tema}"]`);
    return choice?.querySelector('strong')?.textContent?.trim() || tema;
}

function atualizarBuscaPaletas() {
    const input = document.getElementById('paleta-busca');
    const query = (input?.value || '').trim().toLocaleLowerCase('pt-BR');
    const choices = [...document.querySelectorAll('.theme-choice')];
    let visibleCount = 0;
    choices.forEach((choice) => {
        const visible = !query || (choice.dataset.search || '').toLocaleLowerCase('pt-BR').includes(query);
        choice.hidden = !visible;
        if (visible) visibleCount += 1;
    });
    const count = document.getElementById('paleta-contagem');
    if (count) count.textContent = `${visibleCount} ${visibleCount === 1 ? 'tema encontrado' : 'temas encontrados'}`;
    const empty = document.getElementById('paleta-vazia');
    if (empty) empty.hidden = visibleCount !== 0;
}

function atualizarEstadoCards(tema) {
    document.querySelectorAll('.theme-choice').forEach((choice) => {
        const selected = choice.dataset.palette === tema;
        choice.classList.toggle('selected', selected);
        choice.setAttribute('aria-checked', selected ? 'true' : 'false');
        const label = choice.querySelector('.theme-choice-action-label');
        if (label) label.textContent = selected ? 'Tema selecionado' : 'Selecionar tema';
    });
    document.querySelectorAll('#paleta-atual-nome, #perfil-paleta-atual-nome').forEach((currentName) => {
        currentName.textContent = obterNomeTema(tema);
    });
    const badge = document.getElementById('paleta-atual-badge');
    if (badge) badge.dataset.currentTheme = tema;
}

function aplicarTema(tema) {
    if (!tema) return;
    document.body.setAttribute('data-cor', tema);
    temaSelecionado = tema;
    atualizarEstadoCards(tema);
}

async function carregarTema() {
    try {
        const response = await fetch('/perfil/tema');
        if (!response.ok) return;
        const data = await response.json();
        temaOriginal = data.tema_cor || 'paleta-01';
        aplicarTema(temaOriginal);
    } catch (error) {
        console.error('Erro ao carregar tema:', error);
    }
}

async function salvarTema() {
    const button = document.getElementById('btn-salvar-aparencia');
    if (!temaSelecionado || !button) return;
    const originalHtml = button.innerHTML;
    button.disabled = true;
    button.innerHTML = '<span class="spinner-border spinner-border-sm me-2"></span>Aplicando...';
    try {
        const csrf = document.querySelector('[name="csrf_token"]')?.value || '';
        const response = await fetch('/perfil/salvar-tema', {
            method: 'POST',
            headers: {'Content-Type': 'application/json', 'X-CSRFToken': csrf},
            body: JSON.stringify({tema: temaSelecionado})
        });
        const data = await response.json();
        if (!response.ok || !data.success) throw new Error(data.message || 'Não foi possível salvar o tema.');
        temaOriginal = temaSelecionado;
        if (typeof window.showToast === 'function') {
            window.showToast({type: 'success', title: 'Tema aplicado', message: 'A aparência completa do sistema foi atualizada.'});
        }
        const modal = bootstrap.Modal.getInstance(document.getElementById('modalPaletas'));
        if (modal) modal.hide();
    } catch (error) {
        if (typeof window.showToast === 'function') {
            window.showToast({type: 'danger', title: 'Erro ao aplicar tema', message: error.message});
        } else {
            alert(error.message);
        }
        aplicarTema(temaOriginal || 'paleta-01');
    } finally {
        button.disabled = false;
        button.innerHTML = originalHtml;
    }
}

document.addEventListener('DOMContentLoaded', function() {
    carregarTema();
    const choices = [...document.querySelectorAll('.theme-choice')];
    choices.forEach((choice) => {
        choice.addEventListener('click', () => aplicarTema(choice.dataset.palette));
        choice.addEventListener('keydown', (event) => {
            if (!['ArrowRight', 'ArrowDown', 'ArrowLeft', 'ArrowUp'].includes(event.key)) return;
            const visibleChoices = choices.filter((item) => !item.hidden);
            const currentIndex = visibleChoices.indexOf(choice);
            if (currentIndex < 0) return;
            const direction = ['ArrowRight', 'ArrowDown'].includes(event.key) ? 1 : -1;
            const next = visibleChoices[(currentIndex + direction + visibleChoices.length) % visibleChoices.length];
            event.preventDefault();
            next.focus();
            aplicarTema(next.dataset.palette);
        });
    });
    const search = document.getElementById('paleta-busca');
    if (search) {
        search.addEventListener('input', atualizarBuscaPaletas);
        search.addEventListener('keydown', (event) => {
            if (event.key === 'Escape' && search.value) {
                search.value = '';
                atualizarBuscaPaletas();
            }
        });
    }
    atualizarBuscaPaletas();
    const saveButton = document.getElementById('btn-salvar-aparencia');
    if (saveButton) saveButton.addEventListener('click', salvarTema);
});
