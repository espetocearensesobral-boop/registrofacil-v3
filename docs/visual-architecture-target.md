# Arquitetura visual alvo — Registro Fácil 3.19.0

## Objetivo

A arquitetura alvo elimina a disputa entre arquivos e transforma os seis temas em uma fonte consistente de valores. O sistema continuará permitindo a escolha individual de um tema institucional, mas os componentes deixarão de conhecer cores específicas de uma paleta.

> **Princípio central:** temas fornecem valores; componentes fornecem comportamento; módulos fornecem apenas particularidades funcionais; templates fornecem estrutura, não identidade visual.

## Responsabilidade por arquivo

| Camada | Responsabilidade futura | Não deve conter |
|---|---|---|
| `color-themes.css` | Tokens semânticos e os valores das seis paletas. | Regras extensas de componentes, `!important` global ou estilos de template. |
| `visual-system.css` | Tipografia, superfícies, botões, formulários, tabelas, badges, modais, alertas, foco e estados compartilhados. | Hexadecimais de uma paleta, regras de negócio ou layout de módulo. |
| `main.css` | Layout estrutural autenticado, sidebar, navbar, colunas e colapso desktop. | Cores institucionais e estilos de componentes genéricos. |
| `mobile.css` | Breakpoints, drawer da sidebar, navegação mobile e ajustes de toque. | Redefinições globais de botões ou tokens. |
| `compact.css` | Somente densidade e composição compacta de áreas autorizadas. | Segunda versão de todos os componentes Bootstrap. |
| `processos.css` | Estilos específicos do fluxo de processos e timeline. | Regras globais de `.btn`, `.table`, `.form-control` ou `.modal`. |
| `usuarios.css` | Estilos específicos de telas e componentes de usuários. | Tokens ou normalizações globais. |
| `theme.css` e `themes.css` | Compatibilidade transitória durante a migração. | Novas regras de identidade. |
| `palette03-final.css` | Compatibilidade transitória durante a migração. | Novos componentes ou correções adicionais. |
| Templates | Estrutura, classes semânticas e conteúdo. | Cores, famílias tipográficas, sombras e dimensões repetidas em `style=`. |

Durante a migração, `theme.css`, `themes.css` e `palette03-final.css` não serão removidos de imediato. Eles serão congelados, depois esvaziados por grupos e finalmente retirados quando a matriz das seis paletas estiver aprovada.

## Contrato semântico de tokens

Os componentes devem utilizar os tokens abaixo. Os nomes antigos serão mantidos temporariamente como aliases de compatibilidade, mas não poderão ser usados em novos estilos.

| Grupo | Tokens alvo | Uso |
|---|---|---|
| Tipografia | `--rf-font-sans`, `--rf-font-display`, `--rf-font-mono` | Interface, títulos excepcionais e identificadores. |
| Escala | `--rf-font-xs`, `--rf-font-sm`, `--rf-font-base`, `--rf-font-lg`, `--rf-font-xl`, `--rf-font-2xl` | Escala mínima e responsiva. |
| Texto | `--rf-text-primary`, `--rf-text-secondary`, `--rf-text-muted`, `--rf-text-on-primary`, `--rf-text-on-sidebar`, `--rf-text-link` | Hierarquia e contraste. |
| Superfície | `--rf-surface-body`, `--rf-surface-card`, `--rf-surface-muted`, `--rf-surface-input`, `--rf-surface-hover`, `--rf-surface-overlay` | Corpo, cards, campos e overlays. |
| Bordas | `--rf-border`, `--rf-border-subtle`, `--rf-border-input`, `--rf-border-strong` | Separação, campos e estados. |
| Ações | `--rf-action-primary`, `--rf-action-primary-hover`, `--rf-action-primary-active`, `--rf-action-secondary`, `--rf-action-secondary-hover` | Botões e links de ação. |
| Acento | `--rf-accent`, `--rf-accent-hover`, `--rf-accent-subtle` | Destaques institucionais, sem pressupor que todo acento seja dourado. |
| Perigo | `--rf-danger`, `--rf-danger-hover`, `--rf-danger-surface`, `--rf-danger-text` | Exclusão, invalidação e falhas. |
| Sucesso | `--rf-success`, `--rf-success-hover`, `--rf-success-surface`, `--rf-success-text` | Confirmações e conclusão. |
| Aviso | `--rf-warning`, `--rf-warning-hover`, `--rf-warning-surface`, `--rf-warning-text` | Atenção e prazos. |
| Informação | `--rf-info`, `--rf-info-hover`, `--rf-info-surface`, `--rf-info-text` | Ajuda e informação contextual. |
| Sidebar | `--rf-sidebar-surface`, `--rf-sidebar-hover`, `--rf-sidebar-active`, `--rf-sidebar-text`, `--rf-sidebar-active-text`, `--rf-sidebar-border` | Corpo, hover e item ativo da navegação. |
| Geometria | `--rf-radius-sm`, `--rf-radius-md`, `--rf-radius-lg`, `--rf-control-height`, `--rf-sidebar-width` | Dimensões compartilhadas. |
| Elevação | `--rf-shadow-sm`, `--rf-shadow-md`, `--rf-shadow-lg`, `--rf-focus-ring` | Sombras e foco acessível. |

## Contrato das seis paletas

Cada `[data-cor="paleta-XX"]` deverá fornecer todos os tokens semânticos acima. Nenhum token poderá ficar sem valor ou depender de um valor legado definido em `:root`.

A Paleta 04 continuará usando sidebar preta pura. A Paleta 05 continuará sendo testada como sidebar clara, mas deverá fornecer texto, borda, hover e item ativo com contraste próprio. A Paleta 06 manterá o dourado institucional como acento e não como cor de perigo. A semântica do componente determinará se uma cor é ação, acento ou estado; o nome `gold` não será usado como substituto genérico de todas essas funções.

## Cascata alvo

A ordem alvo do layout autenticado será:

1. Bootstrap e Bootstrap Icons.
2. Fonte institucional única.
3. `color-themes.css`.
4. `visual-system.css`.
5. `main.css`.
6. `processos.css` e `usuarios.css` quando aplicáveis.
7. `compact.css` apenas para densidade autorizada.
8. `mobile.css` para breakpoints.
9. Nenhuma camada geral posterior com `!important`.

As telas públicas deverão compartilhar a mesma folha de tokens e a mesma camada de componentes. Seus estilos específicos ficarão limitados ao layout de autenticação e utilizarão os mesmos tokens do tema ativo.

## Estratégia de absorção da camada final

A migração de `palette03-final.css` será feita por grupos: base e superfícies; sidebar; botões; formulários; tabelas; feedback; modais; autenticação; acessibilidade. Cada grupo será transferido para `visual-system.css` ou para `color-themes.css` conforme sua responsabilidade. Depois de cada transferência, os seletores equivalentes nas camadas antigas serão marcados como compatibilidade e não receberão novos ajustes.

A remoção definitiva só ocorrerá quando não houver dependências ativas, os testes de templates passarem e as seis paletas forem verificadas nas larguras de 1440px, 1024px, 768px, 480px e 375px.

## Tipografia alvo

A interface usará **Source Sans 3** como fonte sans-serif principal. **IBM Plex Mono** será usada pela classe `.mono` para matrículas, IDs e atalhos. **Fraunces** ficará restrita a títulos de página ou elementos editoriais aprovados, não a todos os níveis de heading. Os templates não deverão importar Inter ou Segoe UI depois da migração.

## Critérios de aceite da Etapa 2

A arquitetura estará aprovada quando cada arquivo tiver uma responsabilidade única, os tokens semânticos estiverem documentados, as seis paletas fornecerem o contrato completo, a ordem de carregamento estiver definida, a remoção de `palette03-final.css` possuir plano reversível e não houver necessidade de novos `!important` para implementar a Etapa 3.
