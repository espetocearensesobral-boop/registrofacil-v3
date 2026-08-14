// static/js/notifications.js
// Sistema de Notificações Push - Registro Fácil

class NotificationManager {
    constructor() {
        this.permission = null;
        this.checkInterval = 5 * 60 * 1000; // 5 minutos
        this.notificationsShown = new Set(); // Evitar duplicatas
        this.intervalId = null;
        this.enabled = true;
        
        this.init();
    }
    
    async init() {
        // Verificar suporte a notificações
        if (!('Notification' in window)) {
            console.warn('Este navegador não suporta notificações');
            return;
        }
        
        // Solicitar permissão
        this.permission = await this.requestPermission();
        
        if (this.permission === 'granted') {
            // Iniciar verificações periódicas
            this.startChecking();
            
            // Verificação imediata
            this.checkNotifications();
        }
        
        // Configurar listeners
        this.setupEventListeners();
    }
    
    async requestPermission() {
        if (Notification.permission === 'granted') {
            return 'granted';
        }
        
        if (Notification.permission !== 'denied') {
            const permission = await Notification.requestPermission();
            return permission;
        }
        
        return Notification.permission;
    }
    
    setupEventListeners() {
        // Botão para solicitar permissão novamente
        document.addEventListener('click', (e) => {
            if (e.target.matches('[data-enable-notifications]')) {
                this.requestPermission().then(permission => {
                    if (permission === 'granted') {
                        this.startChecking();
                        this.showToast('success', 'Notificações ativadas!');
                    }
                });
            }
        });
        
        // Marcar como lida ao clicar na notificação no dropdown
        document.addEventListener('click', (e) => {
            if (e.target.closest('.notificacao-item[data-notificacao-id]')) {
                const item = e.target.closest('.notificacao-item');
                const notifId = item.dataset.notificacaoId;
                
                if (notifId && !notifId.startsWith('prazo_')) {
                    this.markAsRead(notifId);
                }
            }
        });
        
        // Botão marcar todas como lidas
        document.addEventListener('click', (e) => {
            if (e.target.matches('[data-mark-all-read]')) {
                this.markAllAsRead();
            }
        });
    }
    
    startChecking() {
        if (this.intervalId) {
            clearInterval(this.intervalId);
        }
        
        this.intervalId = setInterval(() => {
            if (this.enabled) {
                this.checkNotifications();
            }
        }, this.checkInterval);
        
        console.log(`Verificação de notificações iniciada (intervalo: ${this.checkInterval / 1000}s)`);
    }
    
    stopChecking() {
        if (this.intervalId) {
            clearInterval(this.intervalId);
            this.intervalId = null;
            console.log('Verificação de notificações parada');
        }
    }
    
    async checkNotifications() {
        try {
            const response = await fetch('/notificacoes/api/pendentes');
            const data = await response.json();
            
            if (data.success && data.notificacoes) {
                // Atualizar badge
                this.updateBadge(data.nao_lidas);
                
                // Atualizar dropdown
                this.updateDropdown(data.notificacoes);
                
                // Mostrar notificações push para novas notificações
                if (this.permission === 'granted') {
                    data.notificacoes.forEach(notif => {
                        // Apenas notificações não lidas e de alta prioridade
                        if (!notif.lida && notif.prioridade === 'alta') {
                            this.showNotification(notif);
                        }
                    });
                }
            }
        } catch (error) {
            console.error('Erro ao verificar notificações:', error);
        }
    }
    
    updateBadge(count) {
        const badge = document.querySelector('.notificacoes-badge');
        if (badge) {
            if (count > 0) {
                badge.textContent = count > 99 ? '99+' : count;
                badge.style.display = 'inline-block';
            } else {
                badge.style.display = 'none';
            }
        }
    }
    
    updateDropdown(notificacoes) {
        const dropdown = document.querySelector('#notificacoes-dropdown-list');
        if (!dropdown) return;
        
        if (notificacoes.length === 0) {
            dropdown.innerHTML = `
                <div class="dropdown-item text-center text-muted py-3">
                    <i class="fas fa-bell-slash"></i><br>
                    Nenhuma notificação
                </div>
            `;
            return;
        }
        
        // Limitar a 10 notificações no dropdown
        const notificacoesLimitadas = notificacoes.slice(0, 10);
        
        dropdown.innerHTML = notificacoesLimitadas.map(notif => {
            const icone = this.getIconePorTipo(notif.tipo);
            const corClass = this.getCorPorPrioridade(notif.prioridade);
            const lida = notif.lida ? 'lida' : '';
            
            return `
                <a href="${notif.url || '#'}" 
                   class="dropdown-item notificacao-item ${lida} ${corClass}" 
                   data-notificacao-id="${notif.id}">
                    <div class="d-flex align-items-start">
                        <div class="notificacao-icon me-2">
                            <i class="fas ${icone}"></i>
                        </div>
                        <div class="flex-grow-1">
                            <div class="notificacao-titulo">${notif.titulo}</div>
                            <div class="notificacao-mensagem">${notif.mensagem}</div>
                            ${notif.created_at ? `<small class="text-muted">${this.formatarData(notif.created_at)}</small>` : ''}
                        </div>
                    </div>
                </a>
            `;
        }).join('');
        
        // Adicionar botão "Ver todas" se houver mais de 10
        if (notificacoes.length > 10) {
            dropdown.innerHTML += `
                <div class="dropdown-divider"></div>
                <a href="/notificacoes" class="dropdown-item text-center text-primary">
                    <i class="fas fa-list"></i> Ver todas (${notificacoes.length})
                </a>
            `;
        }
        
        // Adicionar botão "Marcar todas como lidas" no final
        dropdown.innerHTML += `
            <div class="dropdown-divider"></div>
            <button class="dropdown-item text-center text-muted" data-mark-all-read>
                <i class="fas fa-check-double"></i> Marcar todas como lidas
            </button>
        `;
    }
    
    showNotification(notif) {
        // Evitar mostrar a mesma notificação múltiplas vezes
        const notifKey = `${notif.tipo}_${notif.processo_id || notif.id}`;
        
        if (this.notificationsShown.has(notifKey)) {
            return;
        }
        
        if (this.permission === 'granted') {
            const notification = new Notification(notif.titulo, {
                body: notif.mensagem,
                icon: '/static/img/logo_cartorio.png',
                badge: '/static/img/logo_cartorio.png',
                tag: notifKey,
                requireInteraction: notif.prioridade === 'alta',
                data: { 
                    url: notif.url,
                    id: notif.id
                }
            });
            
            notification.onclick = (event) => {
                event.preventDefault();
                window.focus();
                
                if (notif.url) {
                    window.location.href = notif.url;
                }
                
                // Marcar como lida se for notificação do banco
                if (notif.id && !notif.id.toString().startsWith('prazo_')) {
                    this.markAsRead(notif.id);
                }
                
                notification.close();
            };
            
            // Adicionar ao set de notificações mostradas
            this.notificationsShown.add(notifKey);
            
            // Remover do set após 1 hora para permitir reexibição
            setTimeout(() => {
                this.notificationsShown.delete(notifKey);
            }, 60 * 60 * 1000);
            
            // Reproduzir som (opcional)
            this.playNotificationSound();
        }
    }
    
    async markAsRead(notificacaoId) {
        try {
            const response = await fetch(`/notificacoes/api/${notificacaoId}/marcar-lida`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                }
            });
            
            const data = await response.json();
            
            if (data.success) {
                // Atualizar interface
                this.checkNotifications();
            }
        } catch (error) {
            console.error('Erro ao marcar notificação como lida:', error);
        }
    }
    
    async markAllAsRead() {
        try {
            const response = await fetch('/notificacoes/api/marcar-todas-lidas', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                }
            });
            
            const data = await response.json();
            
            if (data.success) {
                this.showToast('success', 'Todas as notificações foram marcadas como lidas');
                this.checkNotifications();
            }
        } catch (error) {
            console.error('Erro ao marcar todas como lidas:', error);
            this.showToast('error', 'Erro ao atualizar notificações');
        }
    }
    
    getIconePorTipo(tipo) {
        const icones = {
            'prazo_vencendo': 'fa-clock',
            'prazo_vencido': 'fa-exclamation-triangle',
            'processo_atribuido': 'fa-user-tag',
            'processo_atualizado': 'fa-sync',
            'processo_concluido': 'fa-check-circle',
            'comentario': 'fa-comment',
            'sistema': 'fa-info-circle'
        };
        
        return icones[tipo] || 'fa-bell';
    }
    
    getCorPorPrioridade(prioridade) {
        const cores = {
            'alta': 'border-danger',
            'media': 'border-warning',
            'normal': 'border-info',
            'baixa': 'border-secondary'
        };
        
        return cores[prioridade] || '';
    }
    
    formatarData(dataString) {
        const data = new Date(dataString);
        const agora = new Date();
        const diff = Math.floor((agora - data) / 1000); // diferença em segundos
        
        if (diff < 60) {
            return 'Agora';
        } else if (diff < 3600) {
            const minutos = Math.floor(diff / 60);
            return `${minutos} min atrás`;
        } else if (diff < 86400) {
            const horas = Math.floor(diff / 3600);
            return `${horas}h atrás`;
        } else if (diff < 604800) {
            const dias = Math.floor(diff / 86400);
            return `${dias}d atrás`;
        } else {
            return data.toLocaleDateString('pt-BR');
        }
    }
    
    playNotificationSound() {
        // Som de notificação (opcional)
        try {
            const audio = new Audio('/static/sounds/notification.mp3');
            audio.volume = 0.3;
            audio.play().catch(() => {
                // Ignorar erros de reprodução
            });
        } catch (error) {
            // Som não disponível
        }
    }
    
    showToast(type, message) {
        // Integração com sistema de toast existente
        if (typeof showToast === 'function') {
            showToast(type, message);
        } else {
            console.log(`[${type}] ${message}`);
        }
    }
    
    enable() {
        this.enabled = true;
        this.startChecking();
    }
    
    disable() {
        this.enabled = false;
        this.stopChecking();
    }
}

// Inicializar quando o DOM estiver pronto
let notificationManager;

document.addEventListener('DOMContentLoaded', function() {
    notificationManager = new NotificationManager();
    
    // Expor globalmente para uso em outras partes do código
    window.notificationManager = notificationManager;
});

// Verificar quando a página ganha foco (usuário voltou para a aba)
document.addEventListener('visibilitychange', function() {
    if (!document.hidden && notificationManager) {
        // Verificar notificações imediatamente ao voltar para a aba
        notificationManager.checkNotifications();
    }
});
