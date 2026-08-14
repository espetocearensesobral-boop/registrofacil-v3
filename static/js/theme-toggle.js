// static/js/theme-toggle.js
// Sistema de Toggle de Tema - Claro/Escuro

class ThemeManager {
    constructor() {
        this.currentTheme = 'light';
        this.storageKey = 'registrofacil-theme';
        this.toggleBtn = null;
        this.themeIcon = null;
        
        this.init();
    }
    
    init() {
        // Carregar tema salvo ou detectar preferência do sistema
        this.loadTheme();
        
        // Criar botão de toggle se não existir
        this.createToggleButton();
        
        // Aplicar tema
        this.applyTheme(this.currentTheme);
        
        // Configurar event listeners
        this.setupEventListeners();
        
        // Ouvir mudanças de preferência do sistema
        this.watchSystemPreference();
    }
    
    loadTheme() {
        // 1. Verificar localStorage
        const savedTheme = localStorage.getItem(this.storageKey);
        
        if (savedTheme) {
            this.currentTheme = savedTheme;
            return;
        }
        
        // 2. Verificar preferência do sistema
        if (window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches) {
            this.currentTheme = 'dark';
        } else {
            this.currentTheme = 'light';
        }
    }
    
    createToggleButton() {
        // Verificar se já existe
        this.toggleBtn = document.getElementById('theme-toggle-btn');
        
        if (!this.toggleBtn) {
            // Criar botão dinamicamente
            this.toggleBtn = document.createElement('button');
            this.toggleBtn.id = 'theme-toggle-btn';
            this.toggleBtn.className = 'btn btn-sm theme-toggle ms-2';
            this.toggleBtn.setAttribute('title', 'Alternar tema');
            this.toggleBtn.setAttribute('aria-label', 'Alternar tema');
            
            this.themeIcon = document.createElement('i');
            this.themeIcon.id = 'theme-icon';
            this.toggleBtn.appendChild(this.themeIcon);
            
            // Adicionar ao navbar (tentar múltiplos locais)
            const navbar = document.querySelector('.navbar-nav') || 
                          document.querySelector('.navbar') ||
                          document.querySelector('header');
            
            if (navbar) {
                navbar.appendChild(this.toggleBtn);
            }
        } else {
            this.themeIcon = document.getElementById('theme-icon') || 
                           this.toggleBtn.querySelector('i');
        }
        
        // Atualizar ícone
        this.updateIcon();
    }
    
    setupEventListeners() {
        if (this.toggleBtn) {
            this.toggleBtn.addEventListener('click', () => {
                this.toggle();
            });
        }
        
        // Atalho de teclado: Ctrl/Cmd + Shift + T
        document.addEventListener('keydown', (e) => {
            if ((e.ctrlKey || e.metaKey) && e.shiftKey && e.key === 'T') {
                e.preventDefault();
                this.toggle();
            }
        });
    }
    
    watchSystemPreference() {
        if (window.matchMedia) {
            const mediaQuery = window.matchMedia('(prefers-color-scheme: dark)');
            
            mediaQuery.addEventListener('change', (e) => {
                // Apenas aplicar se usuário não tiver preferência salva
                const savedTheme = localStorage.getItem(this.storageKey);
                
                if (!savedTheme) {
                    const newTheme = e.matches ? 'dark' : 'light';
                    this.applyTheme(newTheme);
                }
            });
        }
    }
    
    toggle() {
        const newTheme = this.currentTheme === 'light' ? 'dark' : 'light';
        this.applyTheme(newTheme);
        this.saveTheme(newTheme);
        
        // Feedback visual
        this.showFeedback();
    }
    
    applyTheme(theme) {
        this.currentTheme = theme;
        
        // Aplicar atributo data-theme no HTML
        document.documentElement.setAttribute('data-theme', theme);
        
        // Atualizar ícone
        this.updateIcon();
        
        // Emitir evento customizado
        const event = new CustomEvent('themeChanged', { 
            detail: { theme: theme } 
        });
        document.dispatchEvent(event);
    }
    
    saveTheme(theme) {
        localStorage.setItem(this.storageKey, theme);
        
        // Salvar também no servidor (se usuário estiver logado)
        this.saveThemeToServer(theme);
    }
    
    async saveThemeToServer(theme) {
        try {
            // Verificar se há rota de preferências disponível
            const response = await fetch('/notificacoes/api/configuracoes', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    tema: theme
                })
            });
            
            if (!response.ok) {
                console.log('Preferência de tema não sincronizada com servidor');
            }
        } catch (error) {
            // Ignorar erros de sincronização com servidor
            console.log('Tema salvo apenas localmente');
        }
    }
    
    updateIcon() {
        if (!this.themeIcon) return;
        
        // Remover classes antigas
        this.themeIcon.className = '';
        
        // Adicionar nova classe baseada no tema
        if (this.currentTheme === 'light') {
            this.themeIcon.className = 'fas fa-moon';
            if (this.toggleBtn) {
                this.toggleBtn.setAttribute('title', 'Ativar tema escuro');
            }
        } else {
            this.themeIcon.className = 'fas fa-sun';
            if (this.toggleBtn) {
                this.toggleBtn.setAttribute('title', 'Ativar tema claro');
            }
        }
    }
    
    showFeedback() {
        // Animação de feedback visual
        if (this.toggleBtn) {
            this.toggleBtn.classList.add('pulse');
            setTimeout(() => {
                this.toggleBtn.classList.remove('pulse');
            }, 300);
        }
        
        // Toast notification (se disponível)
        const themeName = this.currentTheme === 'light' ? 'claro' : 'escuro';
        
        if (typeof showToast === 'function') {
            showToast('info', `Tema ${themeName} ativado`);
        }
    }
    
    getTheme() {
        return this.currentTheme;
    }
    
    setTheme(theme) {
        if (theme === 'light' || theme === 'dark') {
            this.applyTheme(theme);
            this.saveTheme(theme);
        }
    }
    
    // Método para resetar para preferência do sistema
    resetToSystemPreference() {
        localStorage.removeItem(this.storageKey);
        
        if (window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches) {
            this.applyTheme('dark');
        } else {
            this.applyTheme('light');
        }
        
        this.showFeedback();
    }
}

// CSS para animação de feedback
const style = document.createElement('style');
style.textContent = `
    @keyframes pulse {
        0% { transform: scale(1); }
        50% { transform: scale(1.1); }
        100% { transform: scale(1); }
    }
    
    .theme-toggle.pulse {
        animation: pulse 0.3s ease;
    }
    
    .theme-toggle {
        transition: transform 0.2s, background-color 0.2s;
    }
    
    .theme-toggle:active {
        transform: scale(0.95);
    }
`;
document.head.appendChild(style);

// Inicializar quando o DOM estiver pronto
let themeManager;

if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', function() {
        themeManager = new ThemeManager();
        window.themeManager = themeManager;
    });
} else {
    // DOM já está pronto
    themeManager = new ThemeManager();
    window.themeManager = themeManager;
}

// Expor função helper global
window.toggleTheme = function() {
    if (themeManager) {
        themeManager.toggle();
    }
};

window.getTheme = function() {
    return themeManager ? themeManager.getTheme() : 'light';
};

window.setTheme = function(theme) {
    if (themeManager) {
        themeManager.setTheme(theme);
    }
};
