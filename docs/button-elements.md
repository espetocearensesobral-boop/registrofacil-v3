# Inventário elemento a elemento dos botões

Foram identificados **367 elementos** com classes de ação nos templates.

| # | Arquivo | Linha | Tag | Texto | Classes | Href | Disabled | Estilo inline |
|---:|---|---:|---|---|---|---|---|---|
| 1 | templates/admin/editar_usuario.html | 1 | a | Cancelar | btn btn-warning | {{ url_for('admin_users.users_list') }} | False | - |
| 2 | templates/admin/editar_usuario.html | 1 | a | Dashboard | nav-btn nav-btn-secondary | {{ url_for('auth.dashboard') }} | False | - |
| 3 | templates/admin/editar_usuario.html | 1 | a | Usuários | nav-btn nav-btn-secondary | {{ url_for('admin_users.users_list') }} | False | - |
| 4 | templates/admin/editar_usuario.html | 1 | button | Cancelar | btn btn-link btn-sm p-0 text-danger | - | False | - |
| 5 | templates/admin/editar_usuario.html | 1 | button | Remover Foto | btn btn-outline-danger btn-sm | - | False | - |
| 6 | templates/admin/editar_usuario.html | 1 | button | Salvar Alterações | btn btn-success | - | False | - |
| 7 | templates/admin/gerenciar_usuario.html | 1 | a | Cancelar | btn btn-outline-secondary | {{ url_for('admin_users.users_list') }} | False | - |
| 8 | templates/admin/gerenciar_usuario.html | 1 | a | Voltar | nav-btn nav-btn-secondary | {{ url_for('admin_users.users_list') }} | False | - |
| 9 | templates/admin/gerenciar_usuario.html | 1 | button | - | btn btn-outline-secondary | - | False | - |
| 10 | templates/admin/gerenciar_usuario.html | 1 | button | Salvar Alterações | btn btn-primary | - | False | - |
| 11 | templates/admin/perfil_admin.html | 1 | a | Cancelar | btn btn-outline-secondary | {{ url_for('admin_users.users_list') }} | False | - |
| 12 | templates/admin/perfil_admin.html | 1 | a | Voltar | nav-btn nav-btn-secondary | {{ url_for('admin_users.users_list') }} | False | - |
| 13 | templates/admin/perfil_admin.html | 1 | button | - | btn btn-outline-secondary | - | False | - |
| 14 | templates/admin/perfil_admin.html | 1 | button | Salvar Alterações | btn btn-primary | - | False | - |
| 15 | templates/admin/usuarios.html | 1 | a | - | tbl-btn view | {{ url_for('permissoes.visualizar_permissoes', usuario_id=user_item.id) }} | False | - |
| 16 | templates/admin/usuarios.html | 1 | a | - | tbl-btn edit | {{ url_for('perfil.index', user_id=user_item.id) }} | False | - |
| 17 | templates/admin/usuarios.html | 1 | a | Dashboard | nav-btn nav-btn-secondary | {{ url_for('auth.dashboard') }} | False | - |
| 18 | templates/admin/usuarios.html | 1 | a | Limpar | btn btn-limpar ms-2 | {{ url_for('admin_users.users_list') }} | False | - |
| 19 | templates/admin/usuarios.html | 1 | a | Limpar Filtros | nav-btn nav-btn-secondary | {{ url_for('admin_users.users_list') }} | False | - |
| 20 | templates/admin/usuarios.html | 1 | a | Novo Usuário | nav-btn nav-btn-primary | {{ url_for('auth.novo_usuario') }} | False | - |
| 21 | templates/admin/usuarios.html | 1 | a | Perfis de Permissão | nav-btn nav-btn-secondary | {{ url_for('permissoes.listar_perfis') }} | False | - |
| 22 | templates/admin/usuarios.html | 1 | button | - | tbl-btn del | - | False | - |
| 23 | templates/admin/usuarios.html | 1 | button | - | btn-close btn-close-white | - | False | - |
| 24 | templates/admin/usuarios.html | 1 | button | Cancelar | nav-btn nav-btn-secondary | - | False | - |
| 25 | templates/admin/usuarios.html | 1 | button | Confirmar Inativação | btn btn-danger | - | False | - |
| 26 | templates/admin/usuarios.html | 1 | button | Filtrar | btn-filter-apply | - | False | - |
| 27 | templates/admin/usuarios.html | 1 | span | - | tbl-btn | - | False | opacity:.35;cursor:default; |
| 28 | templates/admin/usuarios.html | 1 | span | - | tbl-btn | - | False | opacity:.25;cursor:default; |
| 29 | templates/apresentantes/editar.html | 1 | a | Apresentantes | nav-btn nav-btn-secondary | {{ url_for('apresentantes.index') }} | False | - |
| 30 | templates/apresentantes/editar.html | 1 | a | Cancelar | nt-btn-cancel | {{ url_for('apresentantes.visualizar', apresentante_id=apresentante.id) }} | False | - |
| 31 | templates/apresentantes/editar.html | 1 | a | Histórico | nav-btn nav-btn-secondary | {{ url_for('apresentantes.visualizar', apresentante_id=apresentante.id) }} | False | - |
| 32 | templates/apresentantes/editar.html | 1 | button | Salvar Alterações | nt-btn-save | - | False | - |
| 33 | templates/apresentantes/index.html | 1 | a | - | nav-btn nav-btn-primary | {{ url_for('apresentantes.editar', apresentante_id=apresentante.id) }} | False | height:28px;padding:0 10px;font-size:12px; |
| 34 | templates/apresentantes/index.html | 1 | a | Histórico | nav-btn nav-btn-info | {{ url_for('apresentantes.visualizar', apresentante_id=apresentante.id) }} | False | height:28px;padding:0 10px;font-size:12px; |
| 35 | templates/apresentantes/index.html | 1 | a | Limpar | nav-btn nav-btn-danger flex-fill | {{ url_for('apresentantes.index') }} | False | justify-content:center; |
| 36 | templates/apresentantes/index.html | 1 | a | Novo Apresentante | nav-btn nav-btn-primary | {{ url_for('apresentantes.novo') }} | False | - |
| 37 | templates/apresentantes/index.html | 1 | button | - | nav-btn nav-btn-danger btn-excluir-apresentante | - | False | height:28px;padding:0 10px;font-size:12px; |
| 38 | templates/apresentantes/index.html | 1 | button | - | btn-close btn-close-white | - | False | - |
| 39 | templates/apresentantes/index.html | 1 | button | Cancelar | nav-btn nav-btn-secondary | - | False | - |
| 40 | templates/apresentantes/index.html | 1 | button | Excluir | nav-btn nav-btn-danger | - | False | - |
| 41 | templates/apresentantes/index.html | 1 | button | Exportar | nav-btn nav-btn-secondary dropdown-toggle | - | False | - |
| 42 | templates/apresentantes/index.html | 1 | button | Filtrar | nav-btn nav-btn-success flex-fill | - | False | - |
| 43 | templates/apresentantes/index.html | 1 | button | Imprimir | nav-btn nav-btn-secondary | - | False | - |
| 44 | templates/apresentantes/index.html | 1 | span | - | nav-btn nav-btn-primary | - | False | height:28px;padding:0 10px;font-size:12px;opacity:.4;cursor:not-allowed;pointer-events:none; |
| 45 | templates/apresentantes/index.html | 1 | span | - | nav-btn nav-btn-danger | - | False | height:28px;padding:0 10px;font-size:12px;opacity:.4;cursor:not-allowed;pointer-events:none; |
| 46 | templates/apresentantes/novo.html | 1 | a | Apresentantes | nav-btn nav-btn-secondary | {{ url_for('apresentantes.index') }} | False | - |
| 47 | templates/apresentantes/novo.html | 1 | a | Cancelar | nt-btn-cancel | {{ url_for('apresentantes.index') }} | False | - |
| 48 | templates/apresentantes/novo.html | 1 | button | Cadastrar Apresentante | nt-btn-save | - | False | - |
| 49 | templates/apresentantes/visualizar.html | 1 | a | Editar | nav-btn nav-btn-primary | {{ url_for('apresentantes.editar', apresentante_id=apresentante.id) }} | False | - |
| 50 | templates/apresentantes/visualizar.html | 1 | a | Ver | nav-btn nav-btn-secondary | {{ url_for('processos.visualizar', processo_id=processo.id) }} | False | height:28px;padding:0 10px;font-size:12px; |
| 51 | templates/apresentantes/visualizar.html | 1 | a | Voltar | nav-btn nav-btn-secondary | {{ url_for('apresentantes.index') }} | False | - |
| 52 | templates/apresentantes/visualizar.html | 1 | button | - | btn-close btn-close-white | - | False | - |
| 53 | templates/apresentantes/visualizar.html | 1 | button | Cancelar | nav-btn nav-btn-secondary | - | False | - |
| 54 | templates/apresentantes/visualizar.html | 1 | button | Excluir | nav-btn nav-btn-danger | - | False | - |
| 55 | templates/apresentantes/visualizar.html | 1 | button | Excluir | nav-btn nav-btn-danger | - | False | - |
| 56 | templates/apresentantes/visualizar.html | 1 | span | Editar | nav-btn nav-btn-secondary | - | False | opacity:.45;cursor:not-allowed;pointer-events:none; |
| 57 | templates/atividades.html | 1 | a | Consultar Processo | btn btn-success | # | False | display:none; |
| 58 | templates/atividades.html | 1 | a | Dashboard | nav-btn nav-btn-secondary | {{ url_for('auth.dashboard') }} | False | - |
| 59 | templates/atividades.html | 1 | a | Limpar | btn-filter-clear | {{ url_for('atividades.historico') }} | False | - |
| 60 | templates/atividades.html | 1 | a | Limpar Filtros | nav-btn nav-btn-secondary | {{ url_for('atividades.historico') }} | False | - |
| 61 | templates/atividades.html | 1 | button | - | btn-close | - | False | - |
| 62 | templates/atividades.html | 1 | button | Fechar | btn btn-danger | - | False | - |
| 63 | templates/atividades.html | 1 | button | Filtrar | btn-filter-apply | - | False | - |
| 64 | templates/atividades.html | 1 | button | {{ acao_tipo }} {% if acao_desc %} : {{ acao_desc }} {% endif %} | btn-acao-clicavel | - | False | - |
| 65 | templates/backup.html | 1 | a | - | nav-btn nav-btn-secondary rf-backup-action | {{ backup.download_url }} | False | - |
| 66 | templates/backup.html | 1 | a | Dashboard | nav-btn nav-btn-secondary | {{ url_for('auth.dashboard') }} | False | - |
| 67 | templates/backup.html | 1 | button | - | nav-btn nav-btn-danger btn-delete-backup rf-backup-action | - | False | - |
| 68 | templates/backup.html | 1 | button | - | nav-btn nav-btn-secondary rf-backup-action | - | False | - |
| 69 | templates/backup.html | 1 | button | - | btn-close btn-close-white | - | False | - |
| 70 | templates/backup.html | 1 | button | Cancelar | nav-btn nav-btn-secondary | - | False | - |
| 71 | templates/backup.html | 1 | button | Excluir Permanentemente | nav-btn nav-btn-danger | - | False | - |
| 72 | templates/backup.html | 1 | button | Gerar Backup Agora | nav-btn nav-btn-primary rf-backup-primary-action | - | False | - |
| 73 | templates/backup.html | 1 | button | Reparar BD | nav-btn rf-backup-warning-action | - | False | - |
| 74 | templates/backup.html | 1 | button | Testar Banco | nav-btn rf-backup-info-action | - | False | - |
| 75 | templates/base.html | 1 | button | - | btn-close btn-close-white | - | False | - |
| 76 | templates/base.html | 1 | button | - | btn-close rf-search-close | - | False | - |
| 77 | templates/base.html | 1 | button | - | btn-close | - | False | - |
| 78 | templates/base.html | 1 | button | - | btn-close btn-close-white rf-about-close | - | False | - |
| 79 | templates/base.html | 1 | button | Cancelar | nav-btn nav-btn-secondary | - | False | - |
| 80 | templates/base.html | 1 | button | Excluir Permanentemente | nav-btn nav-btn-danger | - | False | - |
| 81 | templates/base.html | 1 | button | Fechar | btn btn-secondary | - | False | - |
| 82 | templates/base.html | 1 | button | Fechar | btn btn-secondary | - | False | - |
| 83 | templates/configuracoes.html | 1 | a | Dashboard | nav-btn nav-btn-secondary | {{ url_for('auth.dashboard') }} | False | - |
| 84 | templates/configuracoes.html | 1 | button | - | cfg-ibtn edit | - | False | - |
| 85 | templates/configuracoes.html | 1 | button | - | cfg-ibtn {% if s.ativo %}{% else %}act-on{% endif %} | - | False | - |
| 86 | templates/configuracoes.html | 1 | button | - | cfg-ibtn edit | - | False | - |
| 87 | templates/configuracoes.html | 1 | button | - | cfg-ibtn {% if sv.ativo %}{% else %}act-on{% endif %} | - | False | - |
| 88 | templates/configuracoes.html | 1 | button | - | btn-browse-dir cfg-browse-dir | - | False | - |
| 89 | templates/configuracoes.html | 1 | button | - | btn-close | - | False | - |
| 90 | templates/configuracoes.html | 1 | button | - | btn-close | - | False | - |
| 91 | templates/configuracoes.html | 1 | button | - | btn-close | - | False | - |
| 92 | templates/configuracoes.html | 1 | button | - | btn btn-outline-secondary | - | False | - |
| 93 | templates/configuracoes.html | 1 | button | - | btn btn-outline-secondary | - | False | - |
| 94 | templates/configuracoes.html | 1 | button | Adicionar | cfg-btn-add | - | False | - |
| 95 | templates/configuracoes.html | 1 | button | Adicionar | cfg-btn-add | - | False | - |
| 96 | templates/configuracoes.html | 1 | button | Cancelar | cfg-obtn | - | False | - |
| 97 | templates/configuracoes.html | 1 | button | Cancelar | cfg-obtn | - | False | - |
| 98 | templates/configuracoes.html | 1 | button | Cancelar | cfg-obtn | - | False | - |
| 99 | templates/configuracoes.html | 1 | button | Remover Logo | nav-btn nav-btn-danger cfg-logo-action | - | False | - |
| 100 | templates/configuracoes.html | 1 | button | Restaurar | nav-btn nav-btn-danger | - | False | - |
| 101 | templates/configuracoes.html | 1 | button | Salvar | cfg-sbtn | - | False | - |
| 102 | templates/configuracoes.html | 1 | button | Salvar | cfg-sbtn | - | False | - |
| 103 | templates/configuracoes.html | 1 | button | Salvar | cfg-sbtn | - | False | - |
| 104 | templates/configuracoes.html | 1 | button | Salvar Alterações | nav-btn nav-btn-success | - | False | - |
| 105 | templates/configuracoes.html | 1 | button | Salvar Backup | cfg-sbtn green | - | False | - |
| 106 | templates/configuracoes.html | 1 | button | Selecionar | cfg-sbtn | - | False | - |
| 107 | templates/configuracoes.html | 1 | button | Testar | cfg-sbtn blue | - | False | - |
| 108 | templates/configuracoes.html | 1 | button | Testar SFTP | cfg-sbtn blue | - | False | - |
| 109 | templates/configuracoes.html | 1 | input | - | cfg-modal-input | - | False | - |
| 110 | templates/configuracoes.html | 1 | input | - | cfg-modal-input | - | False | - |
| 111 | templates/configuracoes.html | 1 | input | - | cfg-modal-input | - | False | - |
| 112 | templates/configuracoes.html | 1 | input | - | cfg-modal-input | - | False | - |
| 113 | templates/configuracoes.html | 1 | input | {{ UPLOAD_PROCESSOS_DIR }} | cfg-managed-path | - | False | - |
| 114 | templates/configuracoes.html | 1 | input | {{ backup_config.backup_day_of_month \| default(1) }} | cfg-time | - | False | - |
| 115 | templates/configuracoes.html | 1 | input | {{ backup_config.backup_time \| default('02:00') }} | cfg-time | - | False | - |
| 116 | templates/configuracoes.html | 1 | input | {{ backup_config.local_path \| default(DEFAULT_BACKUP_PATH) }} | cfg-path-input | - | False | - |
| 117 | templates/configuracoes.html | 1 | input | {{ backup_config.sftp_port\|default(22) }} | cfg-port | - | False | - |
| 118 | templates/configuracoes.html | 1 | span | - | cfg-status-dot | - | False | background:{{s.hex_color}}; |
| 119 | templates/configuracoes.html | 1 | span | * | cfg-required | - | False | - |
| 120 | templates/configuracoes.html | 1 | span | * | cfg-required | - | False | - |
| 121 | templates/configuracoes.html | 1 | span | * | cfg-required | - | False | - |
| 122 | templates/configuracoes.html | 1 | span | * | cfg-required | - | False | - |
| 123 | templates/configuracoes.html | 1 | span | * | cfg-required | - | False | - |
| 124 | templates/configuracoes.html | 1 | span | * | cfg-required | - | False | - |
| 125 | templates/configuracoes.html | 1 | span | * | cfg-required | - | False | - |
| 126 | templates/configuracoes.html | 1 | span | * | cfg-required | - | False | - |
| 127 | templates/configuracoes.html | 1 | span | * | cfg-required | - | False | - |
| 128 | templates/configuracoes.html | 1 | span | * | cfg-required | - | False | - |
| 129 | templates/configuracoes.html | 1 | span | * | cfg-required | - | False | - |
| 130 | templates/configuracoes.html | 1 | span | * | cfg-required | - | False | - |
| 131 | templates/configuracoes.html | 1 | span | * | cfg-required | - | False | - |
| 132 | templates/configuracoes.html | 1 | span | Alterar | cfg-label-upper | - | False | - |
| 133 | templates/configuracoes.html | 1 | span | {% if s.ativo %}Ativo{% else %}Inativo{% endif %} | cfg-status-badge | - | False | background:{% if s.ativo %}var(--color-success){% else %}var(--text-color-secondary){% endif %}; |
| 134 | templates/configuracoes.html | 1 | span | {% if sv.ativo %}Ativo{% else %}Inativo{% endif %} | cfg-status-badge | - | False | background:{% if sv.ativo %}var(--color-success){% else %}var(--text-color-secondary){% endif %}; |
| 135 | templates/configuracoes.html | 1 | span | {{s.nome}} | cfg-status-inline | - | False | - |
| 136 | templates/configuracoes.html | 1 | span | — | cfg-muted | - | False | - |
| 137 | templates/configuracoes.html | 1 | span | — | cfg-muted | - | False | - |
| 138 | templates/dashboard.html | 1 | a | Métricas | nav-btn nav-btn-secondary | {{ url_for('dashboard.metricas') }} | False | - |
| 139 | templates/dashboard.html | 1 | a | Novo Processo | nav-btn nav-btn-primary | {{ url_for('processos.novo') }} | False | - |
| 140 | templates/dashboard.html | 1 | a | Pendentes | nav-btn nav-btn-secondary dashboard-action-link | {{ url_for('processos.pendentes') }} | False | height:26px;padding:0 10px;font-size: .75rem; |
| 141 | templates/dashboard.html | 1 | a | Ver todos | nav-btn nav-btn-secondary dashboard-action-link | {{ url_for('processos.todos') }} | False | height:26px;padding:0 10px;font-size: .75rem; |
| 142 | templates/em_andamento.html | 1 | a | Baixar como PDF | btn btn-dark btn-lg | # | False | - |
| 143 | templates/em_andamento.html | 1 | a | Imprimir | btn btn-dark btn-lg | # | False | - |
| 144 | templates/em_andamento.html | 1 | a | Limpar | btn-filter-clear | {{ url_for('processos.em_andamento') }} | False | - |
| 145 | templates/em_andamento.html | 1 | a | Novo Processo | nav-btn nav-btn-primary | {{ url_for('processos.novo') }} | False | - |
| 146 | templates/em_andamento.html | 1 | button | - | btn-close | - | False | - |
| 147 | templates/em_andamento.html | 1 | button | Exportar | nav-btn nav-btn-secondary dropdown-toggle | - | False | - |
| 148 | templates/em_andamento.html | 1 | button | Fechar | btn btn-outline-secondary | - | False | - |
| 149 | templates/em_andamento.html | 1 | button | Filtrar | btn-filter-apply | - | False | - |
| 150 | templates/em_andamento.html | 1 | button | Imprimir | nav-btn nav-btn-secondary | - | False | - |
| 151 | templates/empresa.html | 1 | a | Cancelar | nav-btn nav-btn-secondary | {{ url_for('auth.dashboard') }} | False | - |
| 152 | templates/empresa.html | 1 | a | Voltar | nav-btn nav-btn-secondary | {{ url_for('auth.dashboard') }} | False | - |
| 153 | templates/empresa.html | 1 | button | Remover Logo | nav-btn nav-btn-secondary | - | False | width:100%;justify-content:center;font-size:12px; |
| 154 | templates/empresa.html | 1 | button | Salvar Alterações | nav-btn nav-btn-success | - | False | - |
| 155 | templates/hoje.html | 1 | a | Baixar como PDF | btn btn-dark btn-lg | # | False | - |
| 156 | templates/hoje.html | 1 | a | Imprimir | btn btn-dark btn-lg | # | False | - |
| 157 | templates/hoje.html | 1 | a | Limpar Filtros do Dia | btn-filter-clear | {{ url_for('processos.hoje') }} | False | - |
| 158 | templates/hoje.html | 1 | a | Novo Processo | nav-btn nav-btn-primary | {{ url_for('processos.novo') }} | False | - |
| 159 | templates/hoje.html | 1 | button | - | btn-close | - | False | - |
| 160 | templates/hoje.html | 1 | button | Exportar | nav-btn nav-btn-secondary dropdown-toggle | - | False | - |
| 161 | templates/hoje.html | 1 | button | Fechar | btn btn-outline-secondary | - | False | - |
| 162 | templates/hoje.html | 1 | button | Filtrar | btn-filter-apply | - | False | - |
| 163 | templates/hoje.html | 1 | button | Imprimir | nav-btn nav-btn-secondary | - | False | - |
| 164 | templates/login.html | 1 | button | Entrar | auth-btn | - | False | - |
| 165 | templates/logout.html | 1 | a | Cancelar | nav-btn nav-btn-secondary | {{ url_for('auth.dashboard') }} | False | height:40px;padding:0 22px;font-size:14px; |
| 166 | templates/logout.html | 1 | a | Voltar | nav-btn nav-btn-secondary | {{ url_for('auth.dashboard') }} | False | - |
| 167 | templates/logout.html | 1 | button | Confirmar Saída | nav-btn nav-btn-primary | - | False | height:40px;padding:0 22px;font-size:14px; |
| 168 | templates/metricas.html | 1 | a | Dashboard | nav-btn nav-btn-secondary | {{ url_for('auth.dashboard') }} | False | - |
| 169 | templates/metricas.html | 1 | button | Atualizar | nav-btn nav-btn-secondary | - | False | - |
| 170 | templates/metricas.html | 1 | button | Equipe | metricas-tab-btn | - | False | - |
| 171 | templates/metricas.html | 1 | button | Meu Desempenho | metricas-tab-btn active | - | False | - |
| 172 | templates/metricas.html | 1 | button | Visão Geral | metricas-tab-btn | - | False | - |
| 173 | templates/novo_usuario.html | 1 | button | Criar Conta | auth-btn | - | False | - |
| 174 | templates/pendentes.html | 1 | a | Baixar como PDF | btn btn-dark btn-lg | # | False | - |
| 175 | templates/pendentes.html | 1 | a | Imprimir | btn btn-dark btn-lg | # | False | - |
| 176 | templates/pendentes.html | 1 | a | Limpar | btn-filter-clear | {{ url_for('processos.pendentes') }} | False | - |
| 177 | templates/pendentes.html | 1 | a | Novo Processo | nav-btn nav-btn-primary | {{ url_for('processos.novo') }} | False | - |
| 178 | templates/pendentes.html | 1 | button | - | btn-close | - | False | - |
| 179 | templates/pendentes.html | 1 | button | Exportar | nav-btn nav-btn-secondary dropdown-toggle | - | False | - |
| 180 | templates/pendentes.html | 1 | button | Fechar | btn btn-outline-secondary | - | False | - |
| 181 | templates/pendentes.html | 1 | button | Filtrar | btn-filter-apply | - | False | - |
| 182 | templates/pendentes.html | 1 | button | Imprimir | nav-btn nav-btn-secondary | - | False | - |
| 183 | templates/perfil.html | 1 | a | Cancelar | btn btn-danger | {{ url_for('auth.dashboard') }} | False | - |
| 184 | templates/perfil.html | 1 | a | Dashboard | nav-btn nav-btn-secondary | {{ url_for('auth.dashboard') }} | False | - |
| 185 | templates/perfil.html | 1 | button | - | btn btn-outline-secondary | - | False | - |
| 186 | templates/perfil.html | 1 | button | - | btn btn-outline-secondary | - | False | - |
| 187 | templates/perfil.html | 1 | button | - | btn btn-outline-secondary | - | False | - |
| 188 | templates/perfil.html | 1 | button | - | btn-close | - | False | - |
| 189 | templates/perfil.html | 1 | button | Aparência | btn btn-outline-primary btn-sm | - | False | - |
| 190 | templates/perfil.html | 1 | button | Aplicar tema | btn btn-primary | - | False | - |
| 191 | templates/perfil.html | 1 | button | Fechar | btn btn-outline-secondary | - | False | - |
| 192 | templates/perfil.html | 1 | button | Salvar Alterações | btn btn-success | - | False | - |
| 193 | templates/perfil_permissao_detalhe.html | 1 | a | - | nav-btn nav-btn-secondary | {{ url_for('permissoes.visualizar_permissoes', usuario_id=u.id) }} | False | height:26px;padding:0 8px;font-size: .75rem; |
| 194 | templates/perfil_permissao_detalhe.html | 1 | a | Voltar | nav-btn nav-btn-secondary | {{ url_for('permissoes.listar_perfis') }} | False | - |
| 195 | templates/perfil_permissao_detalhe.html | 1 | button | Limpar Tudo | nav-btn nav-btn-secondary | - | False | height:30px;padding:0 12px;font-size:12px; |
| 196 | templates/perfil_permissao_detalhe.html | 1 | button | Salvar Alterações | nav-btn nav-btn-primary | - | False | - |
| 197 | templates/perfil_permissao_detalhe.html | 1 | button | Selecionar Tudo | nav-btn nav-btn-secondary | - | False | height:30px;padding:0 12px;font-size:12px; |
| 198 | templates/perfis_permissao.html | 1 | a | Editar | nav-btn nav-btn-secondary | {{ url_for('permissoes.visualizar_perfil', perfil_id=perfil.id) }} | False | height:28px;padding:0 10px;font-size: .75rem; |
| 199 | templates/perfis_permissao.html | 1 | a | Voltar | nav-btn nav-btn-secondary | {{ url_for('admin_users.users_list') }} | False | - |
| 200 | templates/perfis_permissao.html | 1 | button | - | nav-btn nav-btn-secondary | - | False | height:28px;padding:0 10px;font-size: .75rem;color:#dc2626; |
| 201 | templates/perfis_permissao.html | 1 | button | Cancelar | nav-btn nav-btn-secondary | - | False | - |
| 202 | templates/perfis_permissao.html | 1 | button | Criar Perfil | nav-btn nav-btn-primary | - | False | - |
| 203 | templates/perfis_permissao.html | 1 | button | Novo Perfil | nav-btn nav-btn-primary | - | False | - |
| 204 | templates/permissoes_usuario.html | 1 | a | Gerir Perfis | nav-btn nav-btn-secondary | {{ url_for('permissoes.listar_perfis') }} | False | height:30px;padding:0 12px;font-size:12px; |
| 205 | templates/permissoes_usuario.html | 1 | a | Voltar | nav-btn nav-btn-secondary | {{ url_for('admin_users.users_list') }} | False | - |
| 206 | templates/permissoes_usuario.html | 1 | button | Alternar | nav-btn nav-btn-secondary cat-toggle-btn | - | False | height:26px;padding:0 10px;font-size: .75rem;flex-shrink:0; |
| 207 | templates/permissoes_usuario.html | 1 | button | Aplicar Perfil | nav-btn nav-btn-primary | - | False | height:30px;padding:0 12px;font-size:12px; |
| 208 | templates/permissoes_usuario.html | 1 | button | Limpar Tudo | nav-btn nav-btn-secondary | - | False | height:30px;padding:0 12px;font-size:12px; |
| 209 | templates/permissoes_usuario.html | 1 | button | Salvar Alterações | nav-btn | - | False | background:#198754;border-color:#198754;color:#fff;height:38px;padding:0 22px;font-size:13px;font-weight:700;border-radius:8px; |
| 210 | templates/permissoes_usuario.html | 1 | button | Selecionar Tudo | nav-btn nav-btn-secondary | - | False | height:30px;padding:0 12px;font-size:12px; |
| 211 | templates/processos/editar.html | 1 | a | - | btn btn-sm btn-outline-primary | {{ url_for('processos.download_anexo', anexo_id=anexo.id) }} | False | - |
| 212 | templates/processos/editar.html | 1 | a | Cancelar | btn btn-danger | {{ url_for('processos.todos') }} | False | - |
| 213 | templates/processos/editar.html | 1 | a | Todos | nav-btn nav-btn-secondary | {{ url_for('processos.todos') }} | False | - |
| 214 | templates/processos/editar.html | 1 | a | Visualizar | nav-btn nav-btn-secondary | {{ url_for('processos.visualizar', processo_id=processo.id) }} | False | - |
| 215 | templates/processos/editar.html | 1 | button | - | btn-close ms-auto | - | False | - |
| 216 | templates/processos/editar.html | 1 | button | Excluir | nav-btn nav-btn-danger | - | False | - |
| 217 | templates/processos/editar.html | 1 | button | Salvar Alterações | btn btn-success | - | False | - |
| 218 | templates/processos/em_andamento.html | 1 | a | Baixar como PDF | btn btn-dark btn-lg | # | False | - |
| 219 | templates/processos/em_andamento.html | 1 | a | Imprimir | btn btn-dark btn-lg | # | False | - |
| 220 | templates/processos/em_andamento.html | 1 | a | Limpar | btn-filter-clear | {{ url_for('processos.em_andamento') }} | False | - |
| 221 | templates/processos/em_andamento.html | 1 | a | Novo Processo | nav-btn nav-btn-primary | {{ url_for('processos.novo') }} | False | - |
| 222 | templates/processos/em_andamento.html | 1 | button | - | btn-close | - | False | - |
| 223 | templates/processos/em_andamento.html | 1 | button | Exportar | nav-btn nav-btn-secondary dropdown-toggle | - | False | - |
| 224 | templates/processos/em_andamento.html | 1 | button | Fechar | btn btn-outline-secondary | - | False | - |
| 225 | templates/processos/em_andamento.html | 1 | button | Filtrar | btn-filter-apply | - | False | - |
| 226 | templates/processos/em_andamento.html | 1 | button | Imprimir | nav-btn nav-btn-secondary | - | False | - |
| 227 | templates/processos/hoje.html | 1 | a | Baixar como PDF | btn btn-dark btn-lg | # | False | - |
| 228 | templates/processos/hoje.html | 1 | a | Imprimir | btn btn-dark btn-lg | # | False | - |
| 229 | templates/processos/hoje.html | 1 | a | Limpar Filtros do Dia | btn-filter-clear | {{ url_for('processos.hoje') }} | False | - |
| 230 | templates/processos/hoje.html | 1 | a | Novo Processo | nav-btn nav-btn-primary | {{ url_for('processos.novo') }} | False | - |
| 231 | templates/processos/hoje.html | 1 | button | - | btn-close | - | False | - |
| 232 | templates/processos/hoje.html | 1 | button | Exportar | nav-btn nav-btn-secondary dropdown-toggle | - | False | - |
| 233 | templates/processos/hoje.html | 1 | button | Fechar | btn btn-outline-secondary | - | False | - |
| 234 | templates/processos/hoje.html | 1 | button | Filtrar | btn-filter-apply | - | False | - |
| 235 | templates/processos/hoje.html | 1 | button | Imprimir | nav-btn nav-btn-secondary | - | False | - |
| 236 | templates/processos/novo.html | 1 | a | Cancelar | btn btn-danger | {{ url_for('processos.todos') }} | False | - |
| 237 | templates/processos/novo.html | 1 | a | Dashboard | nav-btn nav-btn-secondary | {{ url_for('auth.dashboard') }} | False | - |
| 238 | templates/processos/novo.html | 1 | a | Processos | nav-btn nav-btn-secondary | {{ url_for('processos.todos') }} | False | - |
| 239 | templates/processos/novo.html | 1 | button | Cadastrar Processo | btn btn-success | - | False | - |
| 240 | templates/processos/pendentes.html | 1 | a | Baixar como PDF | btn btn-dark btn-lg | # | False | - |
| 241 | templates/processos/pendentes.html | 1 | a | Imprimir | btn btn-dark btn-lg | # | False | - |
| 242 | templates/processos/pendentes.html | 1 | a | Limpar | btn-filter-clear | {{ url_for('processos.pendentes') }} | False | - |
| 243 | templates/processos/pendentes.html | 1 | a | Novo Processo | nav-btn nav-btn-primary | {{ url_for('processos.novo') }} | False | - |
| 244 | templates/processos/pendentes.html | 1 | button | - | btn-close | - | False | - |
| 245 | templates/processos/pendentes.html | 1 | button | Exportar | nav-btn nav-btn-secondary dropdown-toggle | - | False | - |
| 246 | templates/processos/pendentes.html | 1 | button | Fechar | btn btn-outline-secondary | - | False | - |
| 247 | templates/processos/pendentes.html | 1 | button | Filtrar | btn-filter-apply | - | False | - |
| 248 | templates/processos/pendentes.html | 1 | button | Imprimir | nav-btn nav-btn-secondary | - | False | - |
| 249 | templates/processos/todos.html | 1 | a | - | tbl-btn view | {{ url_for('processos.visualizar', processo_id=processo.id) }} | False | - |
| 250 | templates/processos/todos.html | 1 | a | - | tbl-btn edit | {{ url_for('processos.editar', processo_id=processo.id) }} | False | color:var(--color-warning, #f59e0b); |
| 251 | templates/processos/todos.html | 1 | a | - | tbl-btn edit | {{ url_for('processos.editar', processo_id=processo.id) }} | False | - |
| 252 | templates/processos/todos.html | 1 | a | Baixar como PDF | btn btn-dark btn-lg | # | False | - |
| 253 | templates/processos/todos.html | 1 | a | Imprimir | btn btn-dark btn-lg | # | False | - |
| 254 | templates/processos/todos.html | 1 | a | Limpar | btn-filter-clear | {{ url_for('processos.todos') }} | False | - |
| 255 | templates/processos/todos.html | 1 | a | Novo Processo | nav-btn nav-btn-primary | {{ url_for('processos.novo') }} | False | - |
| 256 | templates/processos/todos.html | 1 | button | - | tbl-btn del | - | False | - |
| 257 | templates/processos/todos.html | 1 | button | - | btn-close | - | False | - |
| 258 | templates/processos/todos.html | 1 | button | Exportar | nav-btn nav-btn-secondary dropdown-toggle | - | False | - |
| 259 | templates/processos/todos.html | 1 | button | Fechar | btn btn-outline-secondary | - | False | - |
| 260 | templates/processos/todos.html | 1 | button | Filtrar | btn-filter-apply | - | False | - |
| 261 | templates/processos/todos.html | 1 | button | Imprimir | nav-btn nav-btn-secondary | - | False | - |
| 262 | templates/processos/vinculados.html | 1 | a | Baixar como PDF | btn btn-dark btn-lg | # | False | - |
| 263 | templates/processos/vinculados.html | 1 | a | Imprimir | btn btn-dark btn-lg | # | False | - |
| 264 | templates/processos/vinculados.html | 1 | a | Limpar | btn-filter-clear | {{ url_for('processos.vinculados') }} | False | - |
| 265 | templates/processos/vinculados.html | 1 | a | Novo Processo | nav-btn nav-btn-primary | {{ url_for('processos.novo') }} | False | - |
| 266 | templates/processos/vinculados.html | 1 | button | - | btn-close | - | False | - |
| 267 | templates/processos/vinculados.html | 1 | button | Exportar | nav-btn nav-btn-secondary dropdown-toggle | - | False | - |
| 268 | templates/processos/vinculados.html | 1 | button | Fechar | btn btn-outline-secondary | - | False | - |
| 269 | templates/processos/vinculados.html | 1 | button | Filtrar | btn-filter-apply | - | False | - |
| 270 | templates/processos/vinculados.html | 1 | button | Imprimir | nav-btn nav-btn-secondary | - | False | - |
| 271 | templates/processos/visualizar.html | 1 | a | Baixar como PDF | btn btn-dark btn-lg | {{ url_for('processos.gerar_pdf', processo_id=processo.id) }} | False | - |
| 272 | templates/processos/visualizar.html | 1 | a | Editar | nav-btn nav-btn-warning | {{ url_for('processos.editar', processo_id=processo.id) }} | False | - |
| 273 | templates/processos/visualizar.html | 1 | a | Editar | nav-btn nav-btn-primary | {{ url_for('processos.editar', processo_id=processo.id) }} | False | - |
| 274 | templates/processos/visualizar.html | 1 | a | Todos | nav-btn nav-btn-secondary | {{ url_for('processos.todos') }} | False | - |
| 275 | templates/processos/visualizar.html | 1 | button | - | btn-close | - | False | - |
| 276 | templates/processos/visualizar.html | 1 | button | - | btn-close btn-close-white | - | False | - |
| 277 | templates/processos/visualizar.html | 1 | button | Cancelar | btn btn-outline-secondary | - | False | - |
| 278 | templates/processos/visualizar.html | 1 | button | Excluir | nav-btn nav-btn-danger | - | False | - |
| 279 | templates/processos/visualizar.html | 1 | button | Excluir Permanentemente | btn btn-danger | - | False | - |
| 280 | templates/processos/visualizar.html | 1 | button | Exibir | btn btn-sm btn-outline-secondary | - | False | - |
| 281 | templates/processos/visualizar.html | 1 | button | Fechar | btn btn-outline-secondary | - | False | - |
| 282 | templates/processos/visualizar.html | 1 | button | Imprimir | nav-btn nav-btn-secondary | - | False | - |
| 283 | templates/processos/visualizar.html | 1 | button | Imprimir Página | btn btn-dark btn-lg | - | False | - |
| 284 | templates/recuperar_senha.html | 1 | button | Enviar Link de Recuperação | auth-btn | - | False | - |
| 285 | templates/representantes/editar.html | 1 | a | Cancelar | nt-btn-cancel | {{ url_for('representantes.visualizar', representante_id=representante.id) }} | False | - |
| 286 | templates/representantes/editar.html | 1 | a | Histórico | nav-btn nav-btn-secondary | {{ url_for('representantes.visualizar', representante_id=representante.id) }} | False | - |
| 287 | templates/representantes/editar.html | 1 | a | Representantes | nav-btn nav-btn-secondary | {{ url_for('representantes.index') }} | False | - |
| 288 | templates/representantes/editar.html | 1 | button | Salvar Alterações | nt-btn-save | - | False | - |
| 289 | templates/representantes/index.html | 1 | a | - | nav-btn nav-btn-primary | {{ url_for('representantes.editar', representante_id=representante.id) }} | False | height:28px;padding:0 10px;font-size:12px; |
| 290 | templates/representantes/index.html | 1 | a | Histórico | nav-btn nav-btn-info | {{ url_for('representantes.visualizar', representante_id=representante.id) }} | False | height:28px;padding:0 10px;font-size:12px; |
| 291 | templates/representantes/index.html | 1 | a | Limpar | nav-btn nav-btn-danger flex-fill | {{ url_for('representantes.index') }} | False | justify-content:center; |
| 292 | templates/representantes/index.html | 1 | a | Novo Representante | nav-btn nav-btn-primary | {{ url_for('representantes.novo') }} | False | - |
| 293 | templates/representantes/index.html | 1 | button | - | nav-btn nav-btn-danger btn-excluir-representante | - | False | height:28px;padding:0 10px;font-size:12px; |
| 294 | templates/representantes/index.html | 1 | button | - | btn-close btn-close-white | - | False | - |
| 295 | templates/representantes/index.html | 1 | button | Cancelar | nav-btn nav-btn-secondary | - | False | - |
| 296 | templates/representantes/index.html | 1 | button | Excluir | nav-btn nav-btn-danger | - | False | - |
| 297 | templates/representantes/index.html | 1 | button | Exportar | nav-btn nav-btn-secondary dropdown-toggle | - | False | - |
| 298 | templates/representantes/index.html | 1 | button | Filtrar | nav-btn nav-btn-success flex-fill | - | False | - |
| 299 | templates/representantes/index.html | 1 | button | Imprimir | nav-btn nav-btn-secondary | - | False | - |
| 300 | templates/representantes/index.html | 1 | span | - | nav-btn nav-btn-primary | - | False | height:28px;padding:0 10px;font-size:12px;opacity:.4;cursor:not-allowed;pointer-events:none; |
| 301 | templates/representantes/index.html | 1 | span | - | nav-btn nav-btn-danger | - | False | height:28px;padding:0 10px;font-size:12px;opacity:.4;cursor:not-allowed;pointer-events:none; |
| 302 | templates/representantes/novo.html | 1 | a | Apresentantes | nav-btn nav-btn-secondary | {{ url_for('representantes.index') }} | False | - |
| 303 | templates/representantes/novo.html | 1 | a | Cancelar | nt-btn-cancel | {{ url_for('representantes.index') }} | False | - |
| 304 | templates/representantes/novo.html | 1 | button | Cadastrar Apresentante | nt-btn-save | - | False | - |
| 305 | templates/representantes/visualizar.html | 1 | a | Editar | nav-btn nav-btn-primary | {{ url_for('representantes.editar', representante_id=representante.id) }} | False | - |
| 306 | templates/representantes/visualizar.html | 1 | a | Ver | nav-btn nav-btn-secondary | {{ url_for('processos.visualizar', processo_id=processo.id) }} | False | height:28px;padding:0 10px;font-size:12px; |
| 307 | templates/representantes/visualizar.html | 1 | a | Voltar | nav-btn nav-btn-secondary | {{ url_for('representantes.index') }} | False | - |
| 308 | templates/representantes/visualizar.html | 1 | button | - | btn-close btn-close-white | - | False | - |
| 309 | templates/representantes/visualizar.html | 1 | button | Cancelar | nav-btn nav-btn-secondary | - | False | - |
| 310 | templates/representantes/visualizar.html | 1 | button | Excluir | nav-btn nav-btn-danger | - | False | - |
| 311 | templates/representantes/visualizar.html | 1 | button | Excluir | nav-btn nav-btn-danger | - | False | - |
| 312 | templates/representantes/visualizar.html | 1 | span | Editar | nav-btn nav-btn-secondary | - | False | opacity:.45;cursor:not-allowed;pointer-events:none; |
| 313 | templates/reset_password.html | 1 | button | Redefinir Senha | auth-btn | - | False | - |
| 314 | templates/titulares/editar.html | 1 | a | Cancelar | nt-btn-cancel | {{ url_for('titulares.visualizar', titular_id=titular.id) }} | False | - |
| 315 | templates/titulares/editar.html | 1 | a | Histórico | nav-btn nav-btn-secondary | {{ url_for('titulares.visualizar', titular_id=titular.id) }} | False | - |
| 316 | templates/titulares/editar.html | 1 | a | Titulares | nav-btn nav-btn-secondary | {{ url_for('titulares.index') }} | False | - |
| 317 | templates/titulares/editar.html | 1 | button | Salvar Alterações | nt-btn-save | - | False | - |
| 318 | templates/titulares/index.html | 1 | a | - | nav-btn nav-btn-primary | {{ url_for('titulares.editar', titular_id=titular.id) }} | False | height:28px;padding:0 10px;font-size:12px; |
| 319 | templates/titulares/index.html | 1 | a | Histórico | nav-btn nav-btn-info | {{ url_for('titulares.visualizar', titular_id=titular.id) }} | False | height:28px;padding:0 10px;font-size:12px; |
| 320 | templates/titulares/index.html | 1 | a | Limpar | nav-btn nav-btn-danger flex-fill | {{ url_for('titulares.index') }} | False | justify-content:center; |
| 321 | templates/titulares/index.html | 1 | a | Novo Titular | nav-btn nav-btn-primary | {{ url_for('titulares.novo') }} | False | - |
| 322 | templates/titulares/index.html | 1 | button | - | nav-btn nav-btn-danger btn-excluir-titular | - | False | height:28px;padding:0 10px;font-size:12px; |
| 323 | templates/titulares/index.html | 1 | button | - | btn-close btn-close-white | - | False | - |
| 324 | templates/titulares/index.html | 1 | button | Cancelar | nav-btn nav-btn-secondary | - | False | - |
| 325 | templates/titulares/index.html | 1 | button | Excluir | nav-btn nav-btn-danger | - | False | - |
| 326 | templates/titulares/index.html | 1 | button | Exportar | nav-btn nav-btn-secondary dropdown-toggle | - | False | - |
| 327 | templates/titulares/index.html | 1 | button | Filtrar | nav-btn nav-btn-success flex-fill | - | False | - |
| 328 | templates/titulares/index.html | 1 | button | Imprimir | nav-btn nav-btn-secondary | - | False | - |
| 329 | templates/titulares/index.html | 1 | span | - | nav-btn nav-btn-primary | - | False | height:28px;padding:0 10px;font-size:12px;opacity:.4;cursor:not-allowed;pointer-events:none; |
| 330 | templates/titulares/index.html | 1 | span | - | nav-btn nav-btn-danger | - | False | height:28px;padding:0 10px;font-size:12px;opacity:.4;cursor:not-allowed;pointer-events:none; |
| 331 | templates/titulares/novo.html | 1 | a | Cancelar | nt-btn-cancel | {{ url_for('titulares.index') }} | False | - |
| 332 | templates/titulares/novo.html | 1 | a | Titulares | nav-btn nav-btn-secondary | {{ url_for('titulares.index') }} | False | - |
| 333 | templates/titulares/novo.html | 1 | button | Cadastrar Titular | nt-btn-save | - | False | - |
| 334 | templates/titulares/visualizar.html | 1 | a | Editar | nav-btn nav-btn-primary | {{ url_for('titulares.editar', titular_id=titular.id) }} | False | - |
| 335 | templates/titulares/visualizar.html | 1 | a | Ver | nav-btn nav-btn-secondary | {{ url_for('processos.visualizar', processo_id=processo.id) }} | False | height:28px;padding:0 10px;font-size:12px; |
| 336 | templates/titulares/visualizar.html | 1 | a | Voltar | nav-btn nav-btn-secondary | {{ url_for('titulares.index') }} | False | - |
| 337 | templates/titulares/visualizar.html | 1 | button | - | btn-close btn-close-white | - | False | - |
| 338 | templates/titulares/visualizar.html | 1 | button | Cancelar | nav-btn nav-btn-secondary | - | False | - |
| 339 | templates/titulares/visualizar.html | 1 | button | Excluir | nav-btn nav-btn-danger | - | False | - |
| 340 | templates/titulares/visualizar.html | 1 | button | Excluir | nav-btn nav-btn-danger | - | False | - |
| 341 | templates/titulares/visualizar.html | 1 | span | Editar | nav-btn nav-btn-secondary | - | False | opacity:.45;cursor:not-allowed;pointer-events:none; |
| 342 | templates/todos.html | 1 | a | - | tbl-btn view | {{ url_for('processos.visualizar', processo_id=processo.id) }} | False | - |
| 343 | templates/todos.html | 1 | a | - | tbl-btn edit | {{ url_for('processos.editar', processo_id=processo.id) }} | False | color:var(--color-warning, #f59e0b); |
| 344 | templates/todos.html | 1 | a | - | tbl-btn edit | {{ url_for('processos.editar', processo_id=processo.id) }} | False | - |
| 345 | templates/todos.html | 1 | a | Baixar como PDF | btn btn-dark btn-lg | # | False | - |
| 346 | templates/todos.html | 1 | a | Imprimir | btn btn-dark btn-lg | # | False | - |
| 347 | templates/todos.html | 1 | a | Limpar | btn-filter-clear | {{ url_for('processos.todos') }} | False | - |
| 348 | templates/todos.html | 1 | a | Novo Processo | nav-btn nav-btn-primary | {{ url_for('processos.novo') }} | False | - |
| 349 | templates/todos.html | 1 | button | - | tbl-btn del | - | False | - |
| 350 | templates/todos.html | 1 | button | - | btn-close | - | False | - |
| 351 | templates/todos.html | 1 | button | Exportar | nav-btn nav-btn-secondary dropdown-toggle | - | False | - |
| 352 | templates/todos.html | 1 | button | Fechar | btn btn-outline-secondary | - | False | - |
| 353 | templates/todos.html | 1 | button | Filtrar | btn-filter-apply | - | False | - |
| 354 | templates/todos.html | 1 | button | Imprimir | nav-btn nav-btn-secondary | - | False | - |
| 355 | templates/visualizar.html | 1 | a | Baixar como PDF | btn btn-dark btn-lg | {{ url_for('processos.gerar_pdf', processo_id=processo.id) }} | False | - |
| 356 | templates/visualizar.html | 1 | a | Editar | nav-btn nav-btn-warning | {{ url_for('processos.editar', processo_id=processo.id) }} | False | - |
| 357 | templates/visualizar.html | 1 | a | Editar | nav-btn nav-btn-primary | {{ url_for('processos.editar', processo_id=processo.id) }} | False | - |
| 358 | templates/visualizar.html | 1 | a | Todos | nav-btn nav-btn-secondary | {{ url_for('processos.todos') }} | False | - |
| 359 | templates/visualizar.html | 1 | button | - | btn-close | - | False | - |
| 360 | templates/visualizar.html | 1 | button | - | btn-close btn-close-white | - | False | - |
| 361 | templates/visualizar.html | 1 | button | Cancelar | btn btn-outline-secondary | - | False | - |
| 362 | templates/visualizar.html | 1 | button | Excluir | nav-btn nav-btn-danger | - | False | - |
| 363 | templates/visualizar.html | 1 | button | Excluir Permanentemente | btn btn-danger | - | False | - |
| 364 | templates/visualizar.html | 1 | button | Exibir | btn btn-sm btn-outline-secondary | - | False | - |
| 365 | templates/visualizar.html | 1 | button | Fechar | btn btn-outline-secondary | - | False | - |
| 366 | templates/visualizar.html | 1 | button | Imprimir | nav-btn nav-btn-secondary | - | False | - |
| 367 | templates/visualizar.html | 1 | button | Imprimir Página | btn btn-dark btn-lg | - | False | - |
