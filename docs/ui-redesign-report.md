# Redesign completo de UI — Registro Fácil

## Objetivo

Aplicar a skill `frontend-ui-engineering` ao sistema Registro Fácil como um produto administrativo completo, não apenas a páginas isoladas. O trabalho cobre autenticação, shell autenticado, dashboard, processos, detalhes, cadastros, configurações, backup, métricas, atividades, auditoria, administração de usuários, permissões, perfil, modais, estados vazios e breakpoints responsivos.

> **Direção visual:** um sistema administrativo institucional, sóbrio e acolhedor, com superfícies neutras, ação principal temática, acento terroso derivado da paleta do projeto, tipografia hierarquizada, bordas discretas, sombras reduzidas e estados de interação claros.

## Sistema visual consolidado

A camada `static/css/internal-ui.css` tornou-se a fonte transversal de acabamento para as telas autenticadas. Ela usa os tokens já existentes em `color-themes.css` — incluindo `--rf-surface-card`, `--rf-border`, `--rf-text-heading`, `--rf-accent`, `--rf-action-primary`, `--rf-danger`, `--rf-success` e `--rf-font-*` — e é carregada no final do `base.html` para vencer estilos inline e blocos legados sem alterar a lógica de negócio.

| Princípio | Aplicação |
| --- | --- |
| Hierarquia | Página, seção, metadado, conteúdo e helper text recebem pesos e tamanhos distintos. |
| Densidade | Cards e toolbars usam a escala do projeto; sombras são pequenas e reservadas a superfícies com elevação real. |
| Cor | A paleta institucional permanece como fonte de ação, acento, status, perigo, sucesso e informação; estados não dependem somente de cor. |
| Componentização | Shell, botões, filtros, tabelas, cards, formulários, modais, badges, pills, vazios, detalhes e timelines possuem contratos globais. |
| Responsividade | A interface começa por uma coluna e expande para grids e tabelas em desktop; listas administrativas viram cartões em mobile. |
| Acessibilidade | Foco visível, labels associados, skip link, `aria-expanded`, `aria-controls`, `aria-live`, alertas semânticos e ações rotuladas. |

## Áreas cobertas

| Área | Redesign entregue |
| --- | --- |
| Autenticação | Login, recuperação, cadastro e redefinição compartilham `auth.css`, com painel institucional, campos, foco, alerts, skip link e toggles de senha acessíveis. |
| Shell | Sidebar, logo, grupos de navegação, item ativo, saída, topbar, menu mobile, ações da página e rodapé foram uniformizados. |
| Dashboard | Saudação, KPIs, recentes, prazos críticos, gráficos, leitura operacional e estados sem dados seguem uma hierarquia de produto operacional. A pontuação duplicada da saudação foi corrigida. |
| Processos | Todas as listas — todos, hoje, pendentes, em andamento e vinculados — usam filtros, tabelas, estados vazios, pills e ações com o mesmo contrato. O formulário de novo/editar processo recebeu campos, seções, anexos, observações e barras de ação responsivas. |
| Detalhe de processo | Dados de titular e apresentante, metadados, status, identificador, observações, anexos, histórico/timeline e modais de relatório/exclusão foram refatorados para classes semânticas; estilos inline de apresentação foram removidos, mantendo somente as variáveis dinâmicas de status. |
| Titulares e apresentantes | Listagens, filtros, ordenação, pills, estados vazios, ações de linha, modais de exclusão, formulários novo/editar e páginas de histórico seguem a mesma linguagem. No mobile, tabelas viram cartões. |
| Configurações e estabelecimento | Abas, status, tipos de serviço, e-mail, estabelecimento, atividades/segurança e sobre mantêm a estrutura funcional com cards, campos, tabela, tabs e mensagens consistentes. |
| Backup | KPIs, status do servidor, última execução, ações de backup, path box, tabela, estado vazio, presença na rede, seleção de diretório, configuração SFTP/automação e modais destrutivos seguem o contrato global. |
| Métricas | Tabs, KPIs, cards comparativos, gráficos, progresso, carregamento, erro, vazio e tabela de equipe usam a mesma escala, bordas, estados e tipografia. |
| Atividades e auditoria | Toolbars de filtro, tabelas infinitas, badges de origem, paginação, detalhes de evento, comparação e metadados recebem o mesmo padrão administrativo. |
| Usuários e permissões | Lista de usuários, filtros, status, ações sensíveis, perfis, categorias de permissão, expansão, contadores, alertas e barras de salvar foram alinhados; a tabela de usuários também é responsiva em cartões. |
| Perfil | Dados pessoais, segurança, toggles de senha, resumo da conta, aparência e modal de tema permanecem em cartões com ações e helpers legíveis. |
| Modais e estados | Confirmações, busca inteligente, atalhos, detalhes, exclusões, configuração, erros e estados vazios compartilham radius, header, footer, foco e contraste. |

## Arquivos centrais

- `static/css/internal-ui.css`
- `static/css/auth.css`
- `static/css/color-themes.css`
- `static/css/visual-system.css`
- `templates/base.html`
- `templates/dashboard.html`
- `templates/processos/visualizar.html`
- `templates/admin/usuarios.html`
- Templates de processos, titulares, apresentantes, configurações, backup, métricas, atividades, auditoria, perfil e permissões.

## Validação

A aplicação Flask foi executada localmente na porta 5055. Foram renderizadas amostras autenticadas de **18 telas** e verificadas prévias em **1440×1000, 768×1000 e 375×1000**. Foram conferidos shell, listas, tabelas, formulários, detalhes, estados vazios, cards analíticos, modais e ações mobile.

A suíte automatizada foi executada com `PYTHONPATH=.` e concluiu com **129 testes aprovados**. Também foram executados `git diff --check`, auditoria de rotas GET autenticadas, verificação de renderização HTML e inspeção das alterações no detalhe de processo. O toggle de histórico foi ajustado para usar `hidden` e `aria-expanded` corretamente.

## Integração com o GitHub

As alterações estão organizadas na branch [`ui/full-system-redesign`](https://github.com/espetocearensesobral-boop/registrofacil-v3/tree/ui/full-system-redesign), derivada de `main`. A branch deve ser revisada visualmente antes do merge. Nenhuma alteração foi feita diretamente na `main`.

## Referências

[1]: https://github.com/espetocearensesobral-boop/registrofacil-v3 "Repositório Registro Fácil v3"
[2]: https://github.com/addyosmani/agent-skills "Repositório de skills frontend-ui-engineering"
