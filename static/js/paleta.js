let temaSelecionado = null;
let temaOriginal = null;

function aplicarTema(tema) {
    if (!tema) return;
    document.body.setAttribute('data-cor', tema);
    temaSelecionado = tema;
    const badge = document.getElementById('paleta-atual-badge');
    if (badge) badge.style.backgroundColor = 'var(--color-primary)';
    document.querySelectorAll('.theme-choice').forEach((choice) => {
        const selected = choice.dataset.palette === tema;
        choice.classList.toggle('selected', selected);
        choice.setAttribute('aria-checked', selected ? 'true' : 'false');
    });
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
    document.querySelectorAll('.theme-choice').forEach((choice) => {
        choice.addEventListener('click', () => aplicarTema(choice.dataset.palette));
    });
    const saveButton = document.getElementById('btn-salvar-aparencia');
    if (saveButton) saveButton.addEventListener('click', salvarTema);
});
