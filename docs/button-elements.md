# Inventário elemento a elemento dos botões

Foram identificados **347 elementos** com classes de ação nos templates.

| # | Arquivo | Linha | Tag | Texto | Classes | Href | Disabled | Estilo inline |
|---:|---|---:|---|---|---|---|---|---|
| 1 | templates/admin/editar_usuario.html | 1 | a | Cancelar | btn btn-warning | {{ url_for('admin_users.users_list') }} | False | - |
| 2 | templates/admin/editar_usuario.html | 1 | a | Dashboard | nav-btn nav-btn-secondary | {{ url_for('auth.dashboard') }} | False | - |
| 3 | templates/admin/editar_usuario.html | 1 | a | Usuários | nav-btn nav-btn-secondary | {{ url_for('admin_users.users_list') }} | False | - |
| 4 | templates/admin/editar_usuario.html | 1 | button | Salvar Alterações | btn btn-success | - | False | - |
| 5 | templates/admin/gerenciar_usuario.html | 1 | a | Cancelar | btn btn-outline-secondary | {{ url_for('admin_users.users_list') }} | False | - |
| 6 | templates/admin/gerenciar_usuario.html | 1 | a | Voltar | nav-btn nav-btn-secondary | {{ url_for('admin_users.users_list') }} | False | - |
| 7 | templates/admin/gerenciar_usuario.html | 1 | button | - | btn btn-outline-secondary | - | False | - |
| 8 | templates/admin/gerenciar_usuario.html | 1 | button | Salvar Alterações | btn btn-primary | - | False | - |
| 9 | templates/admin/perfil_admin.html | 1 | a | Cancelar | btn btn-outline-secondary | {{ url_for('admin_users.users_list') }} | False | - |
| 10 | templates/admin/perfil_admin.html | 1 | a | Voltar | nav-btn nav-btn-secondary | {{ url_for('admin_users.users_list') }} | False | - |
| 11 | templates/admin/perfil_admin.html | 1 | button | - | btn btn-outline-secondary | - | False | - |
| 12 | templates/admin/perfil_admin.html | 1 | button | Salvar Alterações | btn btn-primary | - | False | - |
| 13 | templates/admin/usuarios.html | 1 | a | - | tbl-btn view | {{ url_for('permissoes.visualizar_permissoes', usuario_id=user_item.id) }} | False | - |
| 14 | templates/admin/usuarios.html | 1 | a | - | tbl-btn edit | {{ url_for('perfil.index', user_id=user_item.id) }} | False | - |
| 15 | templates/admin/usuarios.html | 1 | a | Dashboard | nav-btn nav-btn-secondary | {{ url_for('auth.dashboard') }} | False | - |
| 16 | templates/admin/usuarios.html | 1 | a | Limpar | btn btn-limpar ms-2 | {{ url_for('admin_users.users_list') }} | False | - |
| 17 | templates/admin/usuarios.html | 1 | a | Limpar Filtros | nav-btn nav-btn-secondary | {{ url_for('admin_users.users_list') }} | False | - |
| 18 | templates/admin/usuarios.html | 1 | a | Novo Usuário | nav-btn nav-btn-primary | {{ url_for('auth.novo_usuario') }} | False | - |
| 19 | templates/admin/usuarios.html | 1 | a | Perfis de Permissão | nav-btn nav-btn-secondary | {{ url_for('permissoes.listar_perfis') }} | False | - |
| 20 | templates/admin/usuarios.html | 1 | button | - | tbl-btn del | - | False | - |
| 21 | templates/admin/usuarios.html | 1 | button | - | btn-close btn-close-white | - | False | - |
| 22 | templates/admin/usuarios.html | 1 | button | Cancelar | nav-btn nav-btn-secondary | - | False | - |
| 23 | templates/admin/usuarios.html | 1 | button | Confirmar Inativação | btn btn-danger | - | False | - |
| 24 | templates/admin/usuarios.html | 1 | button | Filtrar | btn-filter-apply | - | False | - |
| 25 | templates/admin/usuarios.html | 1 | span | - | tbl-btn | - | False | opacity:.35;cursor:default; |
| 26 | templates/admin/usuarios.html | 1 | span | - | tbl-btn | - | False | opacity:.25;cursor:default; |
| 27 | templates/apresentantes/editar.html | 1 | a | Apresentantes | nav-btn nav-btn-secondary | {{ url_for('apresentantes.index') }} | False | - |
| 28 | templates/apresentantes/editar.html | 1 | a | Cancelar | nt-btn-cancel | {{ url_for('apresentantes.visualizar', apresentante_id=apresentante.id) }} | False | - |
| 29 | templates/apresentantes/editar.html | 1 | a | Histórico | nav-btn nav-btn-secondary | {{ url_for('apresentantes.visualizar', apresentante_id=apresentante.id) }} | False | - |
| 30 | templates/apresentantes/editar.html | 1 | button | Salvar Alterações | nt-btn-save | - | False | - |
| 31 | templates/apresentantes/index.html | 1 | a | - | nav-btn nav-btn-primary btn-xs | {{ url_for('apresentantes.editar', apresentante_id=apresentante.id) }} | False | - |
| 32 | templates/apresentantes/index.html | 1 | a | Histórico | nav-btn nav-btn-info btn-xs | {{ url_for('apresentantes.visualizar', apresentante_id=apresentante.id) }} | False | - |
| 33 | templates/apresentantes/index.html | 1 | a | Limpar | nav-btn nav-btn-danger flex-fill rf-action-center | {{ url_for('apresentantes.index') }} | False | - |
| 34 | templates/apresentantes/index.html | 1 | a | Novo Apresentante | nav-btn nav-btn-primary | {{ url_for('apresentantes.novo') }} | False | - |
| 35 | templates/apresentantes/index.html | 1 | button | - | nav-btn nav-btn-danger btn-excluir-apresentante btn-xs | - | False | - |
| 36 | templates/apresentantes/index.html | 1 | button | - | btn-close btn-close-white | - | False | - |
| 37 | templates/apresentantes/index.html | 1 | button | Cancelar | nav-btn nav-btn-secondary | - | False | - |
| 38 | templates/apresentantes/index.html | 1 | button | Excluir | nav-btn nav-btn-danger | - | False | - |
| 39 | templates/apresentantes/index.html | 1 | button | Exportar | nav-btn nav-btn-secondary dropdown-toggle | - | False | - |
| 40 | templates/apresentantes/index.html | 1 | button | Filtrar | nav-btn nav-btn-success flex-fill | - | False | - |
| 41 | templates/apresentantes/index.html | 1 | button | Imprimir | nav-btn nav-btn-secondary | - | False | - |
| 42 | templates/apresentantes/index.html | 1 | span | - | nav-btn nav-btn-primary btn-xs is-disabled | - | False | - |
| 43 | templates/apresentantes/index.html | 1 | span | - | nav-btn nav-btn-danger btn-xs is-disabled | - | False | - |
| 44 | templates/apresentantes/novo.html | 1 | a | Apresentantes | nav-btn nav-btn-secondary | {{ url_for('apresentantes.index') }} | False | - |
| 45 | templates/apresentantes/novo.html | 1 | a | Cancelar | nt-btn-cancel | {{ url_for('apresentantes.index') }} | False | - |
| 46 | templates/apresentantes/novo.html | 1 | button | Cadastrar Apresentante | nt-btn-save | - | False | - |
| 47 | templates/apresentantes/visualizar.html | 1 | a | Editar | nav-btn nav-btn-primary | {{ url_for('apresentantes.editar', apresentante_id=apresentante.id) }} | False | - |
| 48 | templates/apresentantes/visualizar.html | 1 | a | Ver | nav-btn nav-btn-secondary btn-xs | {{ url_for('processos.visualizar', processo_id=processo.id) }} | False | - |
| 49 | templates/apresentantes/visualizar.html | 1 | a | Voltar | nav-btn nav-btn-secondary | {{ url_for('apresentantes.index') }} | False | - |
| 50 | templates/apresentantes/visualizar.html | 1 | button | - | btn-close btn-close-white | - | False | - |
| 51 | templates/apresentantes/visualizar.html | 1 | button | Cancelar | nav-btn nav-btn-secondary | - | False | - |
| 52 | templates/apresentantes/visualizar.html | 1 | button | Excluir | nav-btn nav-btn-danger | - | False | - |
| 53 | templates/apresentantes/visualizar.html | 1 | button | Excluir | nav-btn nav-btn-danger | - | False | - |
| 54 | templates/apresentantes/visualizar.html | 1 | span | Editar | nav-btn nav-btn-secondary is-disabled | - | False | - |
| 55 | templates/atividades.html | 1 | a | Consultar Processo | btn btn-success | # | False | display:none; |
| 56 | templates/atividades.html | 1 | a | Dashboard | nav-btn nav-btn-secondary | {{ url_for('auth.dashboard') }} | False | - |
| 57 | templates/atividades.html | 1 | a | Limpar | btn-filter-clear | {{ url_for('atividades.historico') }} | False | - |
| 58 | templates/atividades.html | 1 | a | Limpar Filtros | nav-btn nav-btn-secondary | {{ url_for('atividades.historico') }} | False | - |
| 59 | templates/atividades.html | 1 | button | - | btn-close | - | False | - |
| 60 | templates/atividades.html | 1 | button | Fechar | btn btn-danger | - | False | - |
| 61 | templates/atividades.html | 1 | button | Filtrar | btn-filter-apply | - | False | - |
| 62 | templates/atividades.html | 1 | button | {{ acao_tipo }} {% if acao_desc %} : {{ acao_desc }} {% endif %} | btn-acao-clicavel | - | False | - |
| 63 | templates/backup.html | 1 | a | - | nav-btn nav-btn-secondary rf-backup-action | {{ backup.download_url }} | False | - |
| 64 | templates/backup.html | 1 | a | Dashboard | nav-btn nav-btn-secondary | {{ url_for('auth.dashboard') }} | False | - |
| 65 | templates/backup.html | 1 | button | - | nav-btn nav-btn-danger btn-delete-backup rf-backup-action | - | False | - |
| 66 | templates/backup.html | 1 | button | - | nav-btn nav-btn-secondary rf-backup-action | - | False | - |
| 67 | templates/backup.html | 1 | button | - | btn-close btn-close-white | - | False | - |
| 68 | templates/backup.html | 1 | button | Cancelar | nav-btn nav-btn-secondary | - | False | - |
| 69 | templates/backup.html | 1 | button | Excluir Permanentemente | nav-btn nav-btn-danger | - | False | - |
| 70 | templates/backup.html | 1 | button | Gerar Backup Agora | nav-btn nav-btn-primary rf-backup-primary-action | - | False | - |
| 71 | templates/backup.html | 1 | button | Reparar BD | nav-btn rf-backup-warning-action | - | False | - |
| 72 | templates/backup.html | 1 | button | Testar Banco | nav-btn rf-backup-info-action | - | False | - |
| 73 | templates/base.html | 1 | button | - | btn-close btn-close-white | - | False | - |
| 74 | templates/base.html | 1 | button | - | btn-close rf-search-close | - | False | - |
| 75 | templates/base.html | 1 | button | - | btn-close | - | False | - |
| 76 | templates/base.html | 1 | button | - | btn-close btn-close-white rf-about-close | - | False | - |
| 77 | templates/base.html | 1 | button | Cancelar | nav-btn nav-btn-secondary btn-cancel-action | - | False | - |
| 78 | templates/base.html | 1 | button | Excluir Permanentemente | nav-btn nav-btn-danger | - | False | - |
| 79 | templates/base.html | 1 | button | Fechar | btn btn-secondary | - | False | - |
| 80 | templates/base.html | 1 | button | Fechar | btn btn-secondary | - | False | - |
| 81 | templates/configuracoes.html | 1 | a | Dashboard | nav-btn nav-btn-secondary | {{ url_for('auth.dashboard') }} | False | - |
| 82 | templates/configuracoes.html | 1 | button | - | cfg-ibtn edit | - | False | - |
| 83 | templates/configuracoes.html | 1 | button | - | cfg-ibtn {% if s.ativo %}cfg-destructive-toggle{% else %}act-on{% endif %} | - | False | - |
| 84 | templates/configuracoes.html | 1 | button | - | cfg-ibtn edit | - | False | - |
| 85 | templates/configuracoes.html | 1 | button | - | cfg-ibtn {% if sv.ativo %}cfg-destructive-toggle{% else %}act-on{% endif %} | - | False | - |
| 86 | templates/configuracoes.html | 1 | button | - | btn-browse-dir cfg-browse-dir | - | False | - |
| 87 | templates/configuracoes.html | 1 | button | - | btn-close | - | False | - |
| 88 | templates/configuracoes.html | 1 | button | - | btn-close | - | False | - |
| 89 | templates/configuracoes.html | 1 | button | - | btn-close | - | False | - |
| 90 | templates/configuracoes.html | 1 | button | - | btn btn-outline-secondary | - | False | - |
| 91 | templates/configuracoes.html | 1 | button | - | btn btn-outline-secondary | - | False | - |
| 92 | templates/configuracoes.html | 1 | button | Adicionar | cfg-btn-add | - | False | - |
| 93 | templates/configuracoes.html | 1 | button | Adicionar | cfg-btn-add | - | False | - |
| 94 | templates/configuracoes.html | 1 | button | Cancelar | cfg-obtn | - | False | - |
| 95 | templates/configuracoes.html | 1 | button | Cancelar | cfg-obtn | - | False | - |
| 96 | templates/configuracoes.html | 1 | button | Cancelar | cfg-obtn | - | False | - |
| 97 | templates/configuracoes.html | 1 | button | Remover Logo | nav-btn nav-btn-danger cfg-logo-action | - | False | - |
| 98 | templates/configuracoes.html | 1 | button | Restaurar | nav-btn nav-btn-danger | - | False | - |
| 99 | templates/configuracoes.html | 1 | button | Salvar | cfg-sbtn | - | False | - |
| 100 | templates/configuracoes.html | 1 | button | Salvar | cfg-sbtn | - | False | - |
| 101 | templates/configuracoes.html | 1 | button | Salvar | cfg-sbtn | - | False | - |
| 102 | templates/configuracoes.html | 1 | button | Salvar Alterações | nav-btn nav-btn-success | - | False | - |
| 103 | templates/configuracoes.html | 1 | button | Salvar Backup | cfg-sbtn green | - | False | - |
| 104 | templates/configuracoes.html | 1 | button | Selecionar | cfg-sbtn | - | False | - |
| 105 | templates/configuracoes.html | 1 | button | Testar | cfg-sbtn blue | - | False | - |
| 106 | templates/configuracoes.html | 1 | button | Testar SFTP | cfg-sbtn blue | - | False | - |
| 107 | templates/configuracoes.html | 1 | input | - | cfg-modal-input | - | False | - |
| 108 | templates/configuracoes.html | 1 | input | - | cfg-modal-input | - | False | - |
| 109 | templates/configuracoes.html | 1 | input | - | cfg-modal-input | - | False | - |
| 110 | templates/configuracoes.html | 1 | input | - | cfg-modal-input | - | False | - |
| 111 | templates/configuracoes.html | 1 | input | {{ UPLOAD_PROCESSOS_DIR }} | cfg-managed-path | - | False | - |
| 112 | templates/configuracoes.html | 1 | input | {{ backup_config.backup_day_of_month \| default(1) }} | cfg-time | - | False | - |
| 113 | templates/configuracoes.html | 1 | input | {{ backup_config.backup_time \| default('02:00') }} | cfg-time | - | False | - |
| 114 | templates/configuracoes.html | 1 | input | {{ backup_config.local_path \| default(DEFAULT_BACKUP_PATH) }} | cfg-path-input | - | False | - |
| 115 | templates/configuracoes.html | 1 | input | {{ backup_config.sftp_port\|default(22) }} | cfg-port | - | False | - |
| 116 | templates/configuracoes.html | 1 | span | - | cfg-status-dot | - | False | background:{{s.hex_color}}; |
| 117 | templates/configuracoes.html | 1 | span | * | cfg-required | - | False | - |
| 118 | templates/configuracoes.html | 1 | span | * | cfg-required | - | False | - |
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
| 130 | templates/configuracoes.html | 1 | span | Alterar | cfg-label-upper | - | False | - |
| 131 | templates/configuracoes.html | 1 | span | {% if s.ativo %}Ativo{% else %}Inativo{% endif %} | cfg-status-badge | - | False | background:{% if s.ativo %}var(--color-success){% else %}var(--text-color-secondary){% endif %}; |
| 132 | templates/configuracoes.html | 1 | span | {% if sv.ativo %}Ativo{% else %}Inativo{% endif %} | cfg-status-badge | - | False | background:{% if sv.ativo %}var(--color-success){% else %}var(--text-color-secondary){% endif %}; |
| 133 | templates/configuracoes.html | 1 | span | {{s.nome}} | cfg-status-inline | - | False | - |
| 134 | templates/configuracoes.html | 1 | span | — | cfg-muted | - | False | - |
| 135 | templates/configuracoes.html | 1 | span | — | cfg-muted | - | False | - |
| 136 | templates/dashboard.html | 1 | a | Métricas | nav-btn nav-btn-secondary | {{ url_for('dashboard.metricas') }} | False | - |
| 137 | templates/dashboard.html | 1 | a | Novo Processo | nav-btn nav-btn-primary | {{ url_for('processos.novo') }} | False | - |
| 138 | templates/dashboard.html | 1 | a | Pendentes | nav-btn nav-btn-secondary btn-xs dashboard-action-link | {{ url_for('processos.pendentes') }} | False | - |
| 139 | templates/dashboard.html | 1 | a | Ver todos | nav-btn nav-btn-secondary btn-xs dashboard-action-link | {{ url_for('processos.todos') }} | False | - |
| 140 | templates/em_andamento.html | 1 | a | Baixar como PDF | btn btn-dark btn-lg | # | False | - |
| 141 | templates/em_andamento.html | 1 | a | Imprimir | btn btn-dark btn-lg | # | False | - |
| 142 | templates/em_andamento.html | 1 | a | Limpar | btn-filter-clear | {{ url_for('processos.em_andamento') }} | False | - |
| 143 | templates/em_andamento.html | 1 | a | Novo Processo | nav-btn nav-btn-primary | {{ url_for('processos.novo') }} | False | - |
| 144 | templates/em_andamento.html | 1 | button | - | btn-close | - | False | - |
| 145 | templates/em_andamento.html | 1 | button | Exportar | nav-btn nav-btn-secondary dropdown-toggle | - | False | - |
| 146 | templates/em_andamento.html | 1 | button | Fechar | btn btn-outline-secondary | - | False | - |
| 147 | templates/em_andamento.html | 1 | button | Filtrar | btn-filter-apply | - | False | - |
| 148 | templates/em_andamento.html | 1 | button | Imprimir | nav-btn nav-btn-secondary | - | False | - |
| 149 | templates/empresa.html | 1 | a | Cancelar | nav-btn nav-btn-secondary | {{ url_for('auth.dashboard') }} | False | - |
| 150 | templates/empresa.html | 1 | a | Voltar | nav-btn nav-btn-secondary | {{ url_for('auth.dashboard') }} | False | - |
| 151 | templates/empresa.html | 1 | button | Remover Logo | nav-btn nav-btn-secondary btn-w-full | - | False | - |
| 152 | templates/empresa.html | 1 | button | Salvar Alterações | nav-btn nav-btn-success | - | False | - |
| 153 | templates/hoje.html | 1 | a | Baixar como PDF | btn btn-dark btn-lg | # | False | - |
| 154 | templates/hoje.html | 1 | a | Imprimir | btn btn-dark btn-lg | # | False | - |
| 155 | templates/hoje.html | 1 | a | Limpar Filtros do Dia | btn-filter-clear | {{ url_for('processos.hoje') }} | False | - |
| 156 | templates/hoje.html | 1 | a | Novo Processo | nav-btn nav-btn-primary | {{ url_for('processos.novo') }} | False | - |
| 157 | templates/hoje.html | 1 | button | - | btn-close | - | False | - |
| 158 | templates/hoje.html | 1 | button | Exportar | nav-btn nav-btn-secondary dropdown-toggle | - | False | - |
| 159 | templates/hoje.html | 1 | button | Fechar | btn btn-outline-secondary | - | False | - |
| 160 | templates/hoje.html | 1 | button | Filtrar | btn-filter-apply | - | False | - |
| 161 | templates/hoje.html | 1 | button | Imprimir | nav-btn nav-btn-secondary | - | False | - |
| 162 | templates/login.html | 1 | button | Entrar | auth-btn | - | False | - |
| 163 | templates/logout.html | 1 | a | Cancelar | nav-btn nav-btn-secondary btn-cancel-action | {{ url_for('auth.dashboard') }} | False | height:40px;padding:0 22px;font-size:14px; |
| 164 | templates/logout.html | 1 | a | Voltar | nav-btn nav-btn-secondary | {{ url_for('auth.dashboard') }} | False | - |
| 165 | templates/logout.html | 1 | button | Confirmar Saída | nav-btn nav-btn-primary | - | False | height:40px;padding:0 22px;font-size:14px; |
| 166 | templates/metricas.html | 1 | a | Dashboard | nav-btn nav-btn-secondary | {{ url_for('auth.dashboard') }} | False | - |
| 167 | templates/metricas.html | 1 | button | Atualizar | nav-btn nav-btn-secondary | - | False | - |
| 168 | templates/metricas.html | 1 | button | Equipe | metricas-tab-btn | - | False | - |
| 169 | templates/metricas.html | 1 | button | Meu Desempenho | metricas-tab-btn active | - | False | - |
| 170 | templates/metricas.html | 1 | button | Visão Geral | metricas-tab-btn | - | False | - |
| 171 | templates/novo_usuario.html | 1 | button | Criar Conta | auth-btn | - | False | - |
| 172 | templates/pendentes.html | 1 | a | Baixar como PDF | btn btn-dark btn-lg | # | False | - |
| 173 | templates/pendentes.html | 1 | a | Imprimir | btn btn-dark btn-lg | # | False | - |
| 174 | templates/pendentes.html | 1 | a | Limpar | btn-filter-clear | {{ url_for('processos.pendentes') }} | False | - |
| 175 | templates/pendentes.html | 1 | a | Novo Processo | nav-btn nav-btn-primary | {{ url_for('processos.novo') }} | False | - |
| 176 | templates/pendentes.html | 1 | button | - | btn-close | - | False | - |
| 177 | templates/pendentes.html | 1 | button | Exportar | nav-btn nav-btn-secondary dropdown-toggle | - | False | - |
| 178 | templates/pendentes.html | 1 | button | Fechar | btn btn-outline-secondary | - | False | - |
| 179 | templates/pendentes.html | 1 | button | Filtrar | btn-filter-apply | - | False | - |
| 180 | templates/pendentes.html | 1 | button | Imprimir | nav-btn nav-btn-secondary | - | False | - |
| 181 | templates/perfil.html | 1 | a | Cancelar | btn btn-danger btn-cancel-action | {{ url_for('auth.dashboard') }} | False | - |
| 182 | templates/perfil.html | 1 | a | Dashboard | nav-btn nav-btn-secondary | {{ url_for('auth.dashboard') }} | False | - |
| 183 | templates/perfil.html | 1 | button | - | btn btn-outline-secondary | - | False | - |
| 184 | templates/perfil.html | 1 | button | - | btn btn-outline-secondary | - | False | - |
| 185 | templates/perfil.html | 1 | button | - | btn btn-outline-secondary | - | False | - |
| 186 | templates/perfil.html | 1 | button | - | btn-close | - | False | - |
| 187 | templates/perfil.html | 1 | button | Aparência | btn btn-outline-primary btn-sm | - | False | - |
| 188 | templates/perfil.html | 1 | button | Aplicar tema | btn btn-primary | - | False | - |
| 189 | templates/perfil.html | 1 | button | Fechar | btn btn-outline-secondary | - | False | - |
| 190 | templates/perfil.html | 1 | button | Salvar Alterações | btn btn-success | - | False | - |
| 191 | templates/perfil_permissao_detalhe.html | 1 | a | - | nav-btn nav-btn-secondary btn-xs | {{ url_for('permissoes.visualizar_permissoes', usuario_id=u.id) }} | False | - |
| 192 | templates/perfil_permissao_detalhe.html | 1 | a | Voltar | nav-btn nav-btn-secondary | {{ url_for('permissoes.listar_perfis') }} | False | - |
| 193 | templates/perfil_permissao_detalhe.html | 1 | button | Limpar Tudo | nav-btn nav-btn-secondary btn-xs | - | False | - |
| 194 | templates/perfil_permissao_detalhe.html | 1 | button | Salvar Alterações | nav-btn nav-btn-primary | - | False | - |
| 195 | templates/perfil_permissao_detalhe.html | 1 | button | Selecionar Tudo | nav-btn nav-btn-secondary btn-xs | - | False | - |
| 196 | templates/perfis_permissao.html | 1 | a | Editar | nav-btn nav-btn-secondary btn-xs | {{ url_for('permissoes.visualizar_perfil', perfil_id=perfil.id) }} | False | - |
| 197 | templates/perfis_permissao.html | 1 | a | Voltar | nav-btn nav-btn-secondary | {{ url_for('admin_users.users_list') }} | False | - |
| 198 | templates/perfis_permissao.html | 1 | button | - | nav-btn nav-btn-secondary btn-xs rf-action-danger | - | False | - |
| 199 | templates/perfis_permissao.html | 1 | button | - | btn-close | - | False | - |
| 200 | templates/perfis_permissao.html | 1 | button | Cancelar | nav-btn nav-btn-secondary btn-cancel-action | - | False | - |
| 201 | templates/perfis_permissao.html | 1 | button | Criar Perfil | nav-btn nav-btn-primary | - | False | - |
| 202 | templates/perfis_permissao.html | 1 | button | Novo Perfil | nav-btn nav-btn-primary | - | False | - |
| 203 | templates/permissoes_usuario.html | 1 | a | Gerir Perfis | nav-btn nav-btn-secondary btn-xs | {{ url_for('permissoes.listar_perfis') }} | False | - |
| 204 | templates/permissoes_usuario.html | 1 | a | Voltar | nav-btn nav-btn-secondary | {{ url_for('admin_users.users_list') }} | False | - |
| 205 | templates/permissoes_usuario.html | 1 | button | Alternar | nav-btn nav-btn-secondary cat-toggle-btn | - | False | - |
| 206 | templates/permissoes_usuario.html | 1 | button | Aplicar Perfil | nav-btn nav-btn-primary btn-xs | - | False | - |
| 207 | templates/permissoes_usuario.html | 1 | button | Limpar Tudo | nav-btn nav-btn-secondary btn-xs | - | False | - |
| 208 | templates/permissoes_usuario.html | 1 | button | Salvar Alterações | nav-btn | - | False | - |
| 209 | templates/permissoes_usuario.html | 1 | button | Selecionar Tudo | nav-btn nav-btn-secondary btn-xs | - | False | - |
| 210 | templates/processos/editar.html | 1 | a | - | btn btn-sm btn-outline-primary | {{ url_for('processos.download_anexo', anexo_id=anexo.id) }} | False | - |
| 211 | templates/processos/editar.html | 1 | a | Cancelar | btn btn-danger btn-cancel-action | {{ url_for('processos.todos') }} | False | - |
| 212 | templates/processos/editar.html | 1 | a | Todos | nav-btn nav-btn-secondary | {{ url_for('processos.todos') }} | False | - |
| 213 | templates/processos/editar.html | 1 | a | Visualizar | nav-btn nav-btn-secondary | {{ url_for('processos.visualizar', processo_id=processo.id) }} | False | - |
| 214 | templates/processos/editar.html | 1 | button | - | btn-close ms-auto | - | False | - |
| 215 | templates/processos/editar.html | 1 | button | Excluir | nav-btn nav-btn-danger | - | False | - |
| 216 | templates/processos/editar.html | 1 | button | Salvar Alterações | btn btn-success | - | False | - |
| 217 | templates/processos/em_andamento.html | 1 | a | Baixar como PDF | btn btn-dark btn-lg | # | False | - |
| 218 | templates/processos/em_andamento.html | 1 | a | Imprimir | btn btn-dark btn-lg | # | False | - |
| 219 | templates/processos/em_andamento.html | 1 | a | Limpar | btn-filter-clear | {{ url_for('processos.em_andamento') }} | False | - |
| 220 | templates/processos/em_andamento.html | 1 | a | Novo Processo | nav-btn nav-btn-primary | {{ url_for('processos.novo') }} | False | - |
| 221 | templates/processos/em_andamento.html | 1 | button | - | btn-close | - | False | - |
| 222 | templates/processos/em_andamento.html | 1 | button | Exportar | nav-btn nav-btn-secondary dropdown-toggle | - | False | - |
| 223 | templates/processos/em_andamento.html | 1 | button | Fechar | btn btn-outline-secondary | - | False | - |
| 224 | templates/processos/em_andamento.html | 1 | button | Filtrar | btn-filter-apply | - | False | - |
| 225 | templates/processos/em_andamento.html | 1 | button | Imprimir | nav-btn nav-btn-secondary | - | False | - |
| 226 | templates/processos/hoje.html | 1 | a | Baixar como PDF | btn btn-dark btn-lg | # | False | - |
| 227 | templates/processos/hoje.html | 1 | a | Imprimir | btn btn-dark btn-lg | # | False | - |
| 228 | templates/processos/hoje.html | 1 | a | Limpar Filtros do Dia | btn-filter-clear | {{ url_for('processos.hoje') }} | False | - |
| 229 | templates/processos/hoje.html | 1 | a | Novo Processo | nav-btn nav-btn-primary | {{ url_for('processos.novo') }} | False | - |
| 230 | templates/processos/hoje.html | 1 | button | - | btn-close | - | False | - |
| 231 | templates/processos/hoje.html | 1 | button | Exportar | nav-btn nav-btn-secondary dropdown-toggle | - | False | - |
| 232 | templates/processos/hoje.html | 1 | button | Fechar | btn btn-outline-secondary | - | False | - |
| 233 | templates/processos/hoje.html | 1 | button | Filtrar | btn-filter-apply | - | False | - |
| 234 | templates/processos/hoje.html | 1 | button | Imprimir | nav-btn nav-btn-secondary | - | False | - |
| 235 | templates/processos/novo.html | 1 | a | Cancelar | btn btn-danger btn-cancel-action | {{ url_for('processos.todos') }} | False | - |
| 236 | templates/processos/novo.html | 1 | a | Dashboard | nav-btn nav-btn-secondary | {{ url_for('auth.dashboard') }} | False | - |
| 237 | templates/processos/novo.html | 1 | a | Processos | nav-btn nav-btn-secondary | {{ url_for('processos.todos') }} | False | - |
| 238 | templates/processos/novo.html | 1 | button | Cadastrar Processo | btn btn-success | - | False | - |
| 239 | templates/processos/pendentes.html | 1 | a | Baixar como PDF | btn btn-dark btn-lg | # | False | - |
| 240 | templates/processos/pendentes.html | 1 | a | Imprimir | btn btn-dark btn-lg | # | False | - |
| 241 | templates/processos/pendentes.html | 1 | a | Limpar | btn-filter-clear | {{ url_for('processos.pendentes') }} | False | - |
| 242 | templates/processos/pendentes.html | 1 | a | Novo Processo | nav-btn nav-btn-primary | {{ url_for('processos.novo') }} | False | - |
| 243 | templates/processos/pendentes.html | 1 | button | - | btn-close | - | False | - |
| 244 | templates/processos/pendentes.html | 1 | button | Exportar | nav-btn nav-btn-secondary dropdown-toggle | - | False | - |
| 245 | templates/processos/pendentes.html | 1 | button | Fechar | btn btn-outline-secondary | - | False | - |
| 246 | templates/processos/pendentes.html | 1 | button | Filtrar | btn-filter-apply | - | False | - |
| 247 | templates/processos/pendentes.html | 1 | button | Imprimir | nav-btn nav-btn-secondary | - | False | - |
| 248 | templates/processos/todos.html | 1 | a | - | tbl-btn view | {{ url_for('processos.visualizar', processo_id=processo.id) }} | False | - |
| 249 | templates/processos/todos.html | 1 | a | - | tbl-btn edit | {{ url_for('processos.editar', processo_id=processo.id) }} | False | color:var(--color-warning, #f59e0b); |
| 250 | templates/processos/todos.html | 1 | a | - | tbl-btn edit | {{ url_for('processos.editar', processo_id=processo.id) }} | False | - |
| 251 | templates/processos/todos.html | 1 | a | Baixar como PDF | btn btn-dark btn-lg | # | False | - |
| 252 | templates/processos/todos.html | 1 | a | Imprimir | btn btn-dark btn-lg | # | False | - |
| 253 | templates/processos/todos.html | 1 | a | Limpar | btn-filter-clear | {{ url_for('processos.todos') }} | False | - |
| 254 | templates/processos/todos.html | 1 | a | Novo Processo | nav-btn nav-btn-primary | {{ url_for('processos.novo') }} | False | - |
| 255 | templates/processos/todos.html | 1 | button | - | tbl-btn del | - | False | - |
| 256 | templates/processos/todos.html | 1 | button | - | btn-close | - | False | - |
| 257 | templates/processos/todos.html | 1 | button | Exportar | nav-btn nav-btn-secondary dropdown-toggle | - | False | - |
| 258 | templates/processos/todos.html | 1 | button | Fechar | btn btn-outline-secondary | - | False | - |
| 259 | templates/processos/todos.html | 1 | button | Filtrar | btn-filter-apply | - | False | - |
| 260 | templates/processos/todos.html | 1 | button | Imprimir | nav-btn nav-btn-secondary | - | False | - |
| 261 | templates/processos/vinculados.html | 1 | a | Baixar como PDF | btn btn-dark btn-lg | # | False | - |
| 262 | templates/processos/vinculados.html | 1 | a | Imprimir | btn btn-dark btn-lg | # | False | - |
| 263 | templates/processos/vinculados.html | 1 | a | Limpar | btn-filter-clear | {{ url_for('processos.vinculados') }} | False | - |
| 264 | templates/processos/vinculados.html | 1 | a | Novo Processo | nav-btn nav-btn-primary | {{ url_for('processos.novo') }} | False | - |
| 265 | templates/processos/vinculados.html | 1 | button | - | btn-close | - | False | - |
| 266 | templates/processos/vinculados.html | 1 | button | Exportar | nav-btn nav-btn-secondary dropdown-toggle | - | False | - |
| 267 | templates/processos/vinculados.html | 1 | button | Fechar | btn btn-outline-secondary | - | False | - |
| 268 | templates/processos/vinculados.html | 1 | button | Filtrar | btn-filter-apply | - | False | - |
| 269 | templates/processos/vinculados.html | 1 | button | Imprimir | nav-btn nav-btn-secondary | - | False | - |
| 270 | templates/processos/visualizar.html | 1 | a | Baixar como PDF | btn btn-dark btn-lg | {{ url_for('processos.gerar_pdf', processo_id=processo.id) }} | False | - |
| 271 | templates/processos/visualizar.html | 1 | a | Editar | nav-btn nav-btn-warning | {{ url_for('processos.editar', processo_id=processo.id) }} | False | - |
| 272 | templates/processos/visualizar.html | 1 | a | Editar | nav-btn nav-btn-primary | {{ url_for('processos.editar', processo_id=processo.id) }} | False | - |
| 273 | templates/processos/visualizar.html | 1 | a | Todos | nav-btn nav-btn-secondary | {{ url_for('processos.todos') }} | False | - |
| 274 | templates/processos/visualizar.html | 1 | button | - | btn-close | - | False | - |
| 275 | templates/processos/visualizar.html | 1 | button | - | btn-close btn-close-white | - | False | - |
| 276 | templates/processos/visualizar.html | 1 | button | Cancelar | btn btn-outline-secondary btn-cancel-action | - | False | - |
| 277 | templates/processos/visualizar.html | 1 | button | Excluir | nav-btn nav-btn-danger | - | False | - |
| 278 | templates/processos/visualizar.html | 1 | button | Excluir Permanentemente | btn btn-danger | - | False | - |
| 279 | templates/processos/visualizar.html | 1 | button | Exibir | btn btn-sm btn-outline-secondary | - | False | - |
| 280 | templates/processos/visualizar.html | 1 | button | Fechar | btn btn-outline-secondary | - | False | - |
| 281 | templates/processos/visualizar.html | 1 | button | Imprimir | nav-btn nav-btn-secondary | - | False | - |
| 282 | templates/processos/visualizar.html | 1 | button | Imprimir Página | btn btn-dark btn-lg | - | False | - |
| 283 | templates/recuperar_senha.html | 1 | button | Enviar Link de Recuperação | auth-btn | - | False | - |
| 284 | templates/relatorios/contatos.html | 1 | a | Exportar CSV | nav-btn nav-btn-secondary | {{ url_for('relatorios.exportar_contatos', busca=busca, origem=origem) }} | False | - |
| 285 | templates/relatorios/contatos.html | 1 | a | Limpar | nav-btn nav-btn-secondary | {{ url_for('relatorios.contatos') }} | False | - |
| 286 | templates/relatorios/contatos.html | 1 | button | Filtrar | nav-btn nav-btn-success flex-fill | - | False | - |
| 287 | templates/relatorios/index.html | 1 | a | Abrir processos | nav-btn nav-btn-primary | {{ url_for('processos.todos') }} | False | - |
| 288 | templates/relatorios/index.html | 1 | a | Apresentantes | nav-btn nav-btn-secondary | {{ url_for('apresentantes.index') }} | False | - |
| 289 | templates/relatorios/index.html | 1 | a | Titulares | nav-btn nav-btn-secondary | {{ url_for('titulares.index') }} | False | - |
| 290 | templates/relatorios/index.html | 1 | a | Ver contatos | nav-btn nav-btn-primary | {{ url_for('relatorios.contatos') }} | False | - |
| 291 | templates/relatorios/index.html | 1 | a | Ver serviços | nav-btn nav-btn-primary | {{ url_for('relatorios.servicos') }} | False | - |
| 292 | templates/relatorios/servicos.html | 1 | a | Exportar CSV | nav-btn nav-btn-secondary | {{ url_for('relatorios.exportar_servicos') }} | False | - |
| 293 | templates/reset_password.html | 1 | button | Redefinir Senha | auth-btn | - | False | - |
| 294 | templates/titulares/editar.html | 1 | a | Cancelar | nt-btn-cancel | {{ url_for('titulares.visualizar', titular_id=titular.id) }} | False | - |
| 295 | templates/titulares/editar.html | 1 | a | Histórico | nav-btn nav-btn-secondary | {{ url_for('titulares.visualizar', titular_id=titular.id) }} | False | - |
| 296 | templates/titulares/editar.html | 1 | a | Titulares | nav-btn nav-btn-secondary | {{ url_for('titulares.index') }} | False | - |
| 297 | templates/titulares/editar.html | 1 | button | Salvar Alterações | nt-btn-save | - | False | - |
| 298 | templates/titulares/index.html | 1 | a | - | nav-btn nav-btn-primary btn-xs | {{ url_for('titulares.editar', titular_id=titular.id) }} | False | - |
| 299 | templates/titulares/index.html | 1 | a | Histórico | nav-btn nav-btn-info btn-xs | {{ url_for('titulares.visualizar', titular_id=titular.id) }} | False | - |
| 300 | templates/titulares/index.html | 1 | a | Limpar | nav-btn nav-btn-danger flex-fill rf-action-center | {{ url_for('titulares.index') }} | False | - |
| 301 | templates/titulares/index.html | 1 | a | Novo Titular | nav-btn nav-btn-primary | {{ url_for('titulares.novo') }} | False | - |
| 302 | templates/titulares/index.html | 1 | button | - | nav-btn nav-btn-danger btn-excluir-titular btn-xs | - | False | - |
| 303 | templates/titulares/index.html | 1 | button | - | btn-close btn-close-white | - | False | - |
| 304 | templates/titulares/index.html | 1 | button | Cancelar | nav-btn nav-btn-secondary btn-cancel-action | - | False | - |
| 305 | templates/titulares/index.html | 1 | button | Excluir | nav-btn nav-btn-danger | - | False | - |
| 306 | templates/titulares/index.html | 1 | button | Exportar | nav-btn nav-btn-secondary dropdown-toggle | - | False | - |
| 307 | templates/titulares/index.html | 1 | button | Filtrar | nav-btn nav-btn-success flex-fill | - | False | - |
| 308 | templates/titulares/index.html | 1 | button | Imprimir | nav-btn nav-btn-secondary | - | False | - |
| 309 | templates/titulares/index.html | 1 | span | - | nav-btn nav-btn-primary btn-xs is-disabled | - | False | - |
| 310 | templates/titulares/index.html | 1 | span | - | nav-btn nav-btn-danger btn-xs is-disabled | - | False | - |
| 311 | templates/titulares/novo.html | 1 | a | Cancelar | nt-btn-cancel | {{ url_for('titulares.index') }} | False | - |
| 312 | templates/titulares/novo.html | 1 | a | Titulares | nav-btn nav-btn-secondary | {{ url_for('titulares.index') }} | False | - |
| 313 | templates/titulares/novo.html | 1 | button | Cadastrar Titular | nt-btn-save | - | False | - |
| 314 | templates/titulares/visualizar.html | 1 | a | Editar | nav-btn nav-btn-primary | {{ url_for('titulares.editar', titular_id=titular.id) }} | False | - |
| 315 | templates/titulares/visualizar.html | 1 | a | Ver | nav-btn nav-btn-secondary btn-xs | {{ url_for('processos.visualizar', processo_id=processo.id) }} | False | - |
| 316 | templates/titulares/visualizar.html | 1 | a | Voltar | nav-btn nav-btn-secondary | {{ url_for('titulares.index') }} | False | - |
| 317 | templates/titulares/visualizar.html | 1 | button | - | btn-close btn-close-white | - | False | - |
| 318 | templates/titulares/visualizar.html | 1 | button | Cancelar | nav-btn nav-btn-secondary btn-cancel-action | - | False | - |
| 319 | templates/titulares/visualizar.html | 1 | button | Excluir | nav-btn nav-btn-danger | - | False | - |
| 320 | templates/titulares/visualizar.html | 1 | button | Excluir | nav-btn nav-btn-danger | - | False | - |
| 321 | templates/titulares/visualizar.html | 1 | span | Editar | nav-btn nav-btn-secondary is-disabled | - | False | - |
| 322 | templates/todos.html | 1 | a | - | tbl-btn view | {{ url_for('processos.visualizar', processo_id=processo.id) }} | False | - |
| 323 | templates/todos.html | 1 | a | - | tbl-btn edit | {{ url_for('processos.editar', processo_id=processo.id) }} | False | color:var(--color-warning, #f59e0b); |
| 324 | templates/todos.html | 1 | a | - | tbl-btn edit | {{ url_for('processos.editar', processo_id=processo.id) }} | False | - |
| 325 | templates/todos.html | 1 | a | Baixar como PDF | btn btn-dark btn-lg | # | False | - |
| 326 | templates/todos.html | 1 | a | Imprimir | btn btn-dark btn-lg | # | False | - |
| 327 | templates/todos.html | 1 | a | Limpar | btn-filter-clear | {{ url_for('processos.todos') }} | False | - |
| 328 | templates/todos.html | 1 | a | Novo Processo | nav-btn nav-btn-primary | {{ url_for('processos.novo') }} | False | - |
| 329 | templates/todos.html | 1 | button | - | tbl-btn del | - | False | - |
| 330 | templates/todos.html | 1 | button | - | btn-close | - | False | - |
| 331 | templates/todos.html | 1 | button | Exportar | nav-btn nav-btn-secondary dropdown-toggle | - | False | - |
| 332 | templates/todos.html | 1 | button | Fechar | btn btn-outline-secondary | - | False | - |
| 333 | templates/todos.html | 1 | button | Filtrar | btn-filter-apply | - | False | - |
| 334 | templates/todos.html | 1 | button | Imprimir | nav-btn nav-btn-secondary | - | False | - |
| 335 | templates/visualizar.html | 1 | a | Baixar como PDF | btn btn-dark btn-lg | {{ url_for('processos.gerar_pdf', processo_id=processo.id) }} | False | - |
| 336 | templates/visualizar.html | 1 | a | Editar | nav-btn nav-btn-warning | {{ url_for('processos.editar', processo_id=processo.id) }} | False | - |
| 337 | templates/visualizar.html | 1 | a | Editar | nav-btn nav-btn-primary | {{ url_for('processos.editar', processo_id=processo.id) }} | False | - |
| 338 | templates/visualizar.html | 1 | a | Todos | nav-btn nav-btn-secondary | {{ url_for('processos.todos') }} | False | - |
| 339 | templates/visualizar.html | 1 | button | - | btn-close | - | False | - |
| 340 | templates/visualizar.html | 1 | button | - | btn-close btn-close-white | - | False | - |
| 341 | templates/visualizar.html | 1 | button | Cancelar | btn btn-outline-secondary btn-cancel-action | - | False | - |
| 342 | templates/visualizar.html | 1 | button | Excluir | nav-btn nav-btn-danger | - | False | - |
| 343 | templates/visualizar.html | 1 | button | Excluir Permanentemente | btn btn-danger | - | False | - |
| 344 | templates/visualizar.html | 1 | button | Exibir | btn btn-sm btn-outline-secondary | - | False | - |
| 345 | templates/visualizar.html | 1 | button | Fechar | btn btn-outline-secondary | - | False | - |
| 346 | templates/visualizar.html | 1 | button | Imprimir | nav-btn nav-btn-secondary | - | False | - |
| 347 | templates/visualizar.html | 1 | button | Imprimir Página | btn btn-dark btn-lg | - | False | - |
