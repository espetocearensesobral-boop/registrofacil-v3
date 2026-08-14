// ============================================================
// SISTEMA DE PALETAS DE CORES (30 Cores Profissionais)
// ============================================================

const PALETAS = [
    { id: 'dourado', nome: 'Dourado Institucional', cor: '#8B6F47', descricao: 'Elegância e tradição' },
    { id: 'azul-marinho', nome: 'Azul Marinho', cor: '#1B3A5C', descricao: 'Seriedade jurídica' },
    { id: 'vinho', nome: 'Vinho Jurídico', cor: '#6B1F2E', descricao: 'Sobriedade e autoridade' },
    { id: 'verde-esmeralda', nome: 'Verde Esmeralda', cor: '#1B5E20', descricao: 'Prosperidade e vigor' },
    { id: 'azul-petroleo', nome: 'Azul Petróleo', cor: '#006064', descricao: 'Profissionalismo moderno' },
    { id: 'roxo-real', nome: 'Roxo Real', cor: '#4A148C', descricao: 'Elegância e luxo' },
    { id: 'azul-royal', nome: 'Azul Royal', cor: '#1A237E', descricao: 'Autoridade e confiança' },
    { id: 'verde-oliva', nome: 'Verde Oliva', cor: '#556B2F', descricao: 'Tradição e equilíbrio' },
    { id: 'terracota', nome: 'Terracota', cor: '#8B4513', descricao: 'Calidez e estabilidade' },
    { id: 'azul-cobalto', nome: 'Azul Cobalto', cor: '#1565C0', descricao: 'Energia e inovação' },
    { id: 'magenta', nome: 'Magenta Sóbrio', cor: '#880E4F', descricao: 'Criatividade e foco' },
    { id: 'cinza-grafite', nome: 'Cinza Grafite', cor: '#37474F', descricao: 'Minimalismo e foco' },
    { id: 'teal', nome: 'Teal Institucional', cor: '#00695C', descricao: 'Equilíbrio e calma' },
    { id: 'indigo', nome: 'Índigo Profundo', cor: '#283593', descricao: 'Sabedoria e clareza' },
    { id: 'ambar', nome: 'Âmbar Escuro', cor: '#B45309', descricao: 'Determinação e brilho' },
    { id: 'verde-floresta', nome: 'Verde Floresta', cor: '#1B4332', descricao: 'Estabilidade e calma' },
    { id: 'azul-aco', nome: 'Azul Aço', cor: '#2C5F7C', descricao: 'Precisão e técnica' },
    { id: 'coral', nome: 'Coral Terroso', cor: '#A0522D', descricao: 'Acolhimento e força' },
    { id: 'lavanda', nome: 'Lavanda Escura', cor: '#5D4E8C', descricao: 'Serenidade e paz' },
    { id: 'preto-classico', nome: 'Preto Clássico', cor: '#1A1A1A', descricao: 'Sofisticação e poder' },
    { id: 'vermelho-rubi', nome: 'Vermelho Rubi', cor: '#991B1B', descricao: 'Paixão e intensidade' },
    { id: 'rosa-antigo', nome: 'Rosa Antigo', cor: '#9D174D', descricao: 'Delicadeza e história' },
    { id: 'laranja-queimado', nome: 'Laranja Queimado', cor: '#9A3412', descricao: 'Energia terrosa' },
    { id: 'verde-jade', nome: 'Verde Jade', cor: '#065F46', descricao: 'Harmonia e saúde' },
    { id: 'azul-meia-noite', nome: 'Azul Meia-Noite', cor: '#0F172A', descricao: 'Profundidade e mistério' },
    { id: 'violeta-ametista', nome: 'Violeta Ametista', cor: '#4C1D95', descricao: 'Espiritualidade' },
    { id: 'marrom-cafe', nome: 'Marrom Café', cor: '#451A03', descricao: 'Robustez e foco' },
    { id: 'cinza-carvao', nome: 'Cinza Carvão', cor: '#1F2937', descricao: 'Modernidade e força' },
    { id: 'verde-salvia', nome: 'Verde Sálvia', cor: '#3F6212', descricao: 'Naturalidade e calma' },
    { id: 'azul-oceano', nome: 'Azul Oceano', cor: '#075985', descricao: 'Liberdade e expansão' }
];

let paletaSelecionada = null;
let paletaOriginal = null;

document.addEventListener('DOMContentLoaded', function() {
    carregarPaletaAtual();
    gerarGridPaletas();
    
    const btnSalvar = document.getElementById('btn-salvar-paleta');
    if (btnSalvar) {
        btnSalvar.addEventListener('click', salvarPaleta);
    }
    
    const modal = document.getElementById('modalPaletas');
    if (modal) {
        modal.addEventListener('hidden.bs.modal', function() {
            if (paletaSelecionada !== paletaOriginal) {
                aplicarPaleta(paletaOriginal, false);
            }
            document.getElementById('paleta-preview').style.display = 'none';
        });
    }
});

function gerarGridPaletas() {
    const grid = document.getElementById('grid-paletas');
    if (!grid) return;
    
    grid.innerHTML = PALETAS.map(paleta => `
        <div class="col-md-6 col-lg-4">
            <div class="paleta-card ${paletaSelecionada === paleta.id ? 'selecionada' : ''}" 
                 data-paleta="${paleta.id}"
                 onclick="selecionarPaleta('${paleta.id}')">
                <div class="paleta-preview-visual">
                    <div class="paleta-cor-principal" style="background-color: ${paleta.cor};"></div>
                    <div class="paleta-cor-derivadas">
                        <div style="background-color: ${ajustarCor(paleta.cor, -20)};"></div>
                        <div style="background-color: ${ajustarCor(paleta.cor, 20)};"></div>
                        <div style="background-color: ${paleta.cor}20;"></div>
                    </div>
                </div>
                <div class="paleta-info">
                    <div class="paleta-nome">${paleta.nome}</div>
                    <div class="paleta-descricao">${paleta.descricao}</div>
                </div>
                <div class="paleta-check">
                    <i class="bi bi-check-circle-fill"></i>
                </div>
            </div>
        </div>
    `).join('');
}

window.selecionarPaleta = function(paletaId) {
    paletaSelecionada = paletaId;
    
    document.querySelectorAll('.paleta-card').forEach(card => {
        card.classList.remove('selecionada');
    });
    
    const cardSelecionado = document.querySelector(`[data-paleta="${paletaId}"]`);
    if (cardSelecionado) {
        cardSelecionado.classList.add('selecionada');
    }
    
    aplicarPaleta(paletaId, true);
    document.getElementById('paleta-preview').style.display = 'block';
}

function calcularContraste(hex) {
    if (!hex) return '#FFFFFF';
    hex = hex.replace('#', '');
    const r = parseInt(hex.substr(0, 2), 16);
    const g = parseInt(hex.substr(2, 2), 16);
    const b = parseInt(hex.substr(4, 2), 16);
    const yiq = (r * 299 + g * 587 + b * 114) / 1000;
    return yiq >= 128 ? '#121212' : '#FFFFFF';
}

function aplicarPaleta(paletaId, salvarLocalStorage = true) {
    document.body.setAttribute('data-cor', paletaId);
    
    if (salvarLocalStorage) {
        localStorage.setItem('registrofacil_tema_cor', paletaId);
    }
    
    const paleta = PALETAS.find(p => p.id === paletaId);
    if (paleta) {
        const contrastColor = calcularContraste(paleta.cor);
        document.documentElement.style.setProperty('--color-primary-contrast', contrastColor);

        const nomeElement = document.getElementById('paleta-atual-nome');
        if (nomeElement) {
            nomeElement.textContent = paleta.nome;
        }
        const badge = document.getElementById('paleta-atual-badge');
        if (badge) {
            badge.style.backgroundColor = 'var(--color-primary)';
        }
    }
}

async function carregarPaletaAtual() {
    try {
        const response = await fetch('/perfil/tema');
        const data = await response.json();
        
        if (data.tema_cor) {
            paletaOriginal = data.tema_cor;
            paletaSelecionada = data.tema_cor;
            aplicarPaleta(data.tema_cor, false);
        }
    } catch (error) {
        console.error('Erro ao carregar tema:', error);
        paletaOriginal = 'dourado';
    }
}

async function salvarPaleta() {
    if (!paletaSelecionada) {
        alert('Selecione uma paleta primeiro.');
        return;
    }
    
    const btnSalvar = document.getElementById('btn-salvar-paleta');
    const oldHtml = btnSalvar.innerHTML;
    btnSalvar.disabled = true;
    btnSalvar.innerHTML = '<span class="spinner-border spinner-border-sm me-2"></span>Salvando...';
    
    try {
        const response = await fetch('/perfil/salvar-tema', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': document.querySelector('[name="csrf_token"]')?.value || ''
            },
            body: JSON.stringify({ tema: paletaSelecionada })
        });
        
        const data = await response.json();
        
        if (data.success) {
            paletaOriginal = paletaSelecionada;
            if (typeof showToast === 'function') {
                showToast('success', data.mensagem);
            } else {
                alert('Salvo com sucesso!');
            }
            const modal = bootstrap.Modal.getInstance(document.getElementById('modalPaletas'));
            if (modal) modal.hide();
        } else {
            throw new Error(data.erro || 'Erro ao salvar');
        }
    } catch (error) {
        console.error('Erro ao salvar tema:', error);
        if (typeof showToast === 'function') {
            showToast('danger', 'Erro ao salvar preferência: ' + error.message);
        }
    } finally {
        btnSalvar.disabled = false;
        btnSalvar.innerHTML = '<i class="bi bi-check-lg me-1"></i>Confirmar Seleção';
    }
}

function ajustarCor(hex, percent) {
    const num = parseInt(hex.replace('#', ''), 16);
    const amt = Math.round(2.55 * percent);
    const R = Math.max(0, Math.min(255, (num >> 16) + amt));
    const G = Math.max(0, Math.min(255, ((num >> 8) & 0x00FF) + amt));
    const B = Math.max(0, Math.min(255, (num & 0x0000FF) + amt));
    return '#' + (0x1000000 + R * 0x10000 + G * 0x100 + B).toString(16).slice(1);
}
