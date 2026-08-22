# Redesign de UI — Registro Fácil

## Objetivo

Aplicar os princípios da skill `frontend-ui-engineering` ao fluxo público e às telas internas autenticadas do projeto [Registro Fácil](https://github.com/espetocearensesobral-boop/registrofacil-v3), preservando rotas Flask, regras de negócio, sistema de temas, filtros, gráficos, formulários e operações administrativas.

> **Direção visual:** produto administrativo contemporâneo, sóbrio e acolhedor, com superfícies neutras, ação principal temática, acento institucional terroso, tipografia hierarquizada, bordas discretas, sombras mínimas e estados de interação claros.

## Escopo entregue

| Área | Implementação | Resultado |
| --- | --- | --- |
| Shell autenticado | Nova camada `static/css/internal-ui.css` carregada pelo `base.html`; sidebar, logo, estado ativo, topbar, menu mobile, ações e rodapé foram refinados com tokens semânticos. | Navegação mais coesa, topbar estável, hierarquia clara e melhor leitura em desktop e mobile. |
| Dashboard | Saudação, KPIs clicáveis, cards de processos recentes, prazos críticos, gráficos e leitura operacional receberam espaçamento, bordas, estados hover/focus e pesos visuais mais consistentes. | A informação prioritária é escaneável sem excesso de sombra ou decoração genérica. |
| Listagem de processos | Toolbar de busca/filtros, selects, ações de impressão/exportação, tabela e estado vazio foram harmonizados. | Ações e filtros são distinguíveis, com maior respiro e feedback visual coerente. |
| Formulário de novo processo | Campos, seções, grupos de dados, observações, anexos e ações herdaram a régua interna; placeholders de `form-floating` foram ocultados para evitar sobreposição com labels. | Formulário mais limpo, especialmente em 375px, mantendo labels semânticos e textos de ajuda. |
| Configurações | Abas, cartões, tabela de status e controles administrativos foram validados com o novo shell. | A página preserva sua estrutura funcional e mantém o estado ativo das abas. |
| Autenticação | `auth.css` compartilhado para login, recuperação, cadastro e redefinição; skip link, `main`/`aside`, alertas semânticos e controles reais de senha. | Fluxo público consistente, responsivo e navegável por teclado. |
| Cascata CSS | Overrides públicos conflitantes foram removidos de `visual-system.css`; heading global foi restrito ao conteúdo autenticado para não atingir a marca da autenticação. | Menos dependência de `!important` legado e uma fonte visual central por contexto. |
| Microcopy | Corrigida a pontuação duplicada na saudação do dashboard. | Primeira leitura mais polida e natural. |

## Arquivos principais

- `static/css/internal-ui.css`
- `static/css/auth.css`
- `static/css/visual-system.css`
- `templates/base.html`
- `templates/dashboard.html`
- `templates/processos/todos.html`
- `templates/processos/novo.html`
- `templates/configuracoes.html`
- `templates/login.html`
- `templates/recuperar_senha.html`
- `templates/novo_usuario.html`
- `templates/reset_password.html`

## Acessibilidade e responsividade

A interface foi revisada com foco em navegação por teclado, estados `:focus-visible`, labels associados, `aria-label`, `aria-controls`, `aria-pressed`, `role="alert"`, skip links e estados vazios significativos. As ações da topbar permanecem rotuladas também no mobile; a navegação lateral continua recebendo enriquecimento de teclado pelo `accessibility.js` existente.

As prévias foram verificadas em 1440×900, 1024×900, 768×900 e 375×900. O shell interno empilha o conteúdo sem criar overflow horizontal; a toolbar da listagem passa para uma coluna legível e os campos do novo processo mantêm alvos de toque confortáveis.

## Validação

A aplicação Flask foi executada localmente na porta 5055. As rotas autenticadas `/dashboard`, `/processos/`, `/processos/novo` e `/configuracoes/` foram renderizadas por uma sessão de QA isolada e verificadas visualmente. As rotas públicas de autenticação também foram verificadas com `auth.css` carregado.

A suíte automatizada foi executada com `PYTHONPATH=.` e concluiu com **129 testes aprovados**. Também foram executados `git diff --check`, checagem estática dos templates, validação de carregamento HTTP e inspeção do console da sessão autenticada sem erros JavaScript relacionados às alterações.

## Integração com o GitHub

As alterações foram aplicadas ao checkout local derivado da branch `main` do repositório informado. A publicação remota deve ocorrer em uma branch de revisão, preservando `main` até a aprovação visual e funcional do usuário.

## Referências

[1]: https://github.com/espetocearensesobral-boop/registrofacil-v3 "Repositório Registro Fácil v3"
[2]: https://github.com/addyosmani/agent-skills "Repositório de skills frontend-ui-engineering"
