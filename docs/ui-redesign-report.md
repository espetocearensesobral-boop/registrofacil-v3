# Redesign completo de UI — RegistroFácil

## Resumo da entrega

Foi concluída uma revisão abrangente da interface do RegistroFácil na branch `ui/full-system-redesign`, sem alteração direta da `main`. O checkout contém **50 arquivos HTML reais**: **49 templates Jinja** em `templates/` e **1 documentação standalone** em `static/documentacao.html`. Os 50 arquivos foram modificados nesta rodada de cobertura integral.

A entrega combina três níveis de trabalho. Primeiro, o sistema visual compartilhado foi reforçado para que shell autenticado, superfícies, cards, tabelas, formulários, filtros, botões, modais, estados vazios, KPIs, detalhes e breakpoints sigam contratos consistentes. Segundo, os templates receberam identificação de superfície e componente para que a estilização seja previsível por domínio. Terceiro, as telas de maior complexidade receberam alterações reais de markup, semântica e acessibilidade, e não apenas atributos de rastreamento.

> A cobertura integral não significa que todos os 50 arquivos precisem de um layout visual isolado. Templates de impressão, parciais e telas que herdam o shell compartilham deliberadamente os mesmos componentes. O critério aplicado foi revisar cada arquivo, preservar seu contrato funcional e garantir que sua superfície participe efetivamente do sistema visual.

## Direção visual

A interface segue uma linguagem administrativa institucional: superfícies neutras, acento terroso derivado do sistema de temas existente, ação primária temática, tipografia hierarquizada, bordas discretas, sombras reduzidas e estados de interação visíveis. Não foram introduzidos gradientes decorativos, paleta roxa genérica ou componentes visualmente desconectados do RegistroFácil.

O tema continua sendo controlado por `data-cor="paleta-XX"` e pelos tokens já fornecidos por `color-themes.css`. A nova camada interna usa tokens semânticos para texto, superfície, borda, foco, ação, sucesso, alerta, perigo e informação, mantendo as 30 paletas existentes como fonte de variação visual.

## Transformações por domínio

| Domínio | Arquivos cobertos | Alterações efetivas |
| --- | --- | --- |
| Shell e autenticação | `base.html`, `login.html`, `novo_usuario.html`, `recuperar_senha.html`, `reset_password.html`, `logout.html` | Shell autenticado, skip link, topbar, sidebar, superfícies, foco, alerts, formulários, navegação e estados públicos alinhados ao sistema visual. |
| Dashboard e processos | `dashboard.html`, `processos/_filter_toolbar.html`, `processos/editar.html`, `processos/em_andamento.html`, `processos/hoje.html`, `processos/novo.html`, `processos/pendentes.html`, `processos/todos.html`, `processos/vinculados.html`, `processos/visualizar.html` | KPIs, cards de leitura operacional, filtros com `role="search"`, tabelas, formulários, upload, anexos, timeline, detalhe e histórico com `hidden`, `aria-expanded` e foco preservado. |
| Titulares | `titulares/index.html`, `titulares/novo.html`, `titulares/editar.html`, `titulares/visualizar.html` | Lista, filtros, cadastros, detalhe, histórico e modais. Na lista, ordenação passou de `onclick` em `<th>` para links reais, com caption, `scope="col"`, seção nomeada e ações rotuladas. |
| Apresentantes | `apresentantes/index.html`, `apresentantes/novo.html`, `apresentantes/editar.html`, `apresentantes/visualizar.html` | Mesmo padrão de titulares com rotas específicas preservadas, links de ordenação acessíveis, caption, ações nomeadas e modal de exclusão identificado. |
| Configurações | `configuracoes.html`, `_config_about_panel.html`, `_config_activity_panel.html`, `_config_event_panel.html` | Abas e painéis semânticos, `aria-controls`, `aria-selected`, foco após salvar/trocar aba, tabelas responsivas, filtros de eventos, estados vazios e componentes de aparência, status, serviços, e-mail e estabelecimento. |
| Backup | `backup.html` | Regiões próprias para resumo, última execução, criação e listagem; tabela com `scope`, `data-label`, ações de ícone com `aria-label`, modais nomeados, presença de usuários e estados de carregamento/erro. |
| Métricas | `metricas.html` | Tabs com `role="tablist"`, `role="tab"` e `role="tabpanel"`, sincronização de `aria-selected`/`aria-hidden`, cartões de gráficos como artigos, KPIs com `aria-live`, estados de carregamento, erro e ausência de dados. |
| Perfil | `perfil.html` e `static/css/layout-standard.css` | Editor, segurança, aparência e informações da conta foram separados em regiões semânticas; rótulos inline duplicados foram removidos e substituídos por classes de domínio. |
| Usuários e permissões | `_users_filter_toolbar.html`, `admin/usuarios.html`, `admin/editar_usuario.html`, `admin/gerenciar_usuario.html`, `admin/perfil_admin.html`, `perfis_permissao.html`, `perfil_permissao_detalhe.html`, `permissoes_usuario.html` | Filtros, cards administrativos, status, ações sensíveis, perfis, permissões, tabelas com `data-label` e transformação mobile para cartões legíveis. |
| Atividades e auditoria | `_activity_filter_toolbar.html`, `atividades.html`, `auditoria.html` | Histórico operacional, filtro semântico, tabela nomeada, ordenação, modal de detalhes, auditoria, paginação identificada, estados vazios e metadados. A URL legada de atividades continua redirecionando para o histórico unificado conforme o blueprint existente. |
| Relatórios | `_cadastros_print_styles.html`, `apresentantes_print.html`, `historico_processo_print.html`, `processos_print.html`, `relatorio_processo_print.html`, `titulares_print.html` | Tokens de impressão, cabeçalhos, resumo, tabela, badges, vazios, rodapé e identidade institucional consistentes. O partial de impressão foi tratado como CSS, não como página de superfície. |
| Documentação standalone | `static/documentacao.html` | Cabeçalho, badge de versão, navegação semântica, foco visível, cartões, tabelas, blocos de código, estados de seção e breakpoints próprios para desktop e mobile. |

## Sistema visual central

O arquivo `static/css/internal-ui.css` foi expandido como camada interna transversal. Ele cobre o shell autenticado, topbar, sidebar, cards, filtros, formulários, tabelas, KPIs, dashboard, detalhes de processo, anexos, timeline, modais, estados vazios, foco e responsividade. O `base.html` identifica a superfície atual no `body` e no `main` e carrega essa camada depois do CSS legado para que os contratos novos prevaleçam sem exigir a remoção imediata de toda regra histórica.

O tratamento mobile transforma listas de cadastros e usuários em cartões legíveis, preserva rótulos por célula com `data-label` e evita depender apenas de cor para comunicar estado. Inputs de busca usam `type="search"`; tabelas receberam cabeçalhos com `scope="col"` e captions visuais ocultas quando necessário; ações que exibem somente ícone possuem nomes acessíveis.

## Funcionalidade preservada

Foram preservados endpoints Flask, nomes de campos, IDs consumidos por JavaScript, destinos de formulários, modais Bootstrap, consultas assíncronas, paginação infinita, ordenação, upload, restauração de backup, sistema de temas e permissões. Em particular, o histórico de processos continua usando a lógica de `data-href` existente no shell, sem conversão arriscada para links que alterariam `main.js` ou `accessibility.js`.

Os estilos inline restantes são deliberados quando representam estado dinâmico controlado por dados ou por JavaScript, por exemplo visibilidade de painéis de backup, cor dinâmica de status e regras específicas de impressão. Estilos decorativos duplicados ou inválidos, como os rótulos inline duplicados do perfil e os handlers de hover inline do seletor de diretório, foram removidos ou centralizados.

## QA executado

A validação técnica foi executada no ambiente real da aplicação. O compilador percorreu os **49 templates Jinja** com `create_app()` e o ambiente Jinja da aplicação, resultando em `compiled=49` e `errors=0`. A suíte automatizada resultou em **129 testes aprovados**. Também foram executados `git diff --check`, auditoria de contagem de HTMLs e verificação de que os 50 arquivos HTML aparecem como modificados.

A QA visual percorreu dashboard, métricas, backup, perfil, configurações/status, histórico unificado de atividades e documentação standalone. Foram verificados estados vazios, tabelas, filtros, KPIs, tabs, cartões, ações administrativas, shell, cabeçalho e breakpoints. As prévias da documentação standalone foram geradas em **1440×1000** e **375×1000** e permanecem legíveis nos dois formatos. As observações detalhadas ficam em `docs/ui-visual-qa-notes.md` e o inventário por arquivo fica em `docs/html-complete-inventory.tsv`.

## Arquivos de apoio versionados

| Arquivo | Finalidade |
| --- | --- |
| `docs/ui-redesign-report.md` | Relatório final desta entrega. |
| `docs/html-complete-inventory.tsv` | Inventário dos 50 HTMLs, linhas, estilos inline, blocos de estilo e herança Jinja. |
| `docs/ui-visual-qa-notes.md` | Registro das telas e estados revisados visualmente. |
| `static/css/internal-ui.css` | Camada visual autenticada transversal. |
| `static/css/layout-standard.css` | Regras de domínio refinadas para o perfil. |
| `static/documentacao.html` | Documentação standalone revisada como o 50º HTML. |

## Integração com o GitHub

As alterações devem ser publicadas na branch [`ui/full-system-redesign`](https://github.com/espetocearensesobral-boop/registrofacil-v3/tree/ui/full-system-redesign), derivada de `main`. A `main` permanece intacta até aprovação explícita para merge.

## Referências

[1]: https://github.com/espetocearensesobral-boop/registrofacil-v3 "Repositório RegistroFácil v3"
[2]: https://github.com/addyosmani/agent-skills "Skill frontend-ui-engineering"
