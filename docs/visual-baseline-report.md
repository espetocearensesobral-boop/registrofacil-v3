# Baseline visual — Registro Fácil 3.19.0

## Escopo

Este baseline mede a situação real do código em 15 de agosto de 2026, antes da consolidação da arquitetura visual. Nenhum comportamento foi alterado durante o inventário.

## Ordem atual de carregamento

### Layout autenticado

1. Bootstrap 5 e Bootstrap Icons via CDN.
2. Fonte Segoe UI via CDN.
3. `themes.css`.
4. `theme.css`.
5. `main.css`.
6. `processos.css`.
7. `usuarios.css`.
8. `compact.css`.
9. `mobile.css`.
10. `color-themes.css`.
11. `visual-system.css`.
12. `palette03-final.css`, carregado no final do corpo do template.

### Telas públicas

Login, criação de usuário, recuperação de senha e redefinição carregam Bootstrap, Bootstrap Icons, Inter, estilos inline próprios, `color-themes.css` e `palette03-final.css`. Portanto, as telas públicas não compartilham a mesma cadeia tipográfica e estrutural do layout autenticado.

## Métricas observadas

| Indicador | Resultado atual |
|---|---:|
| Usos de `!important` em CSS e templates | 666 |
| `!important` em `visual-system.css` | 232 |
| `!important` em `palette03-final.css` | 174 |
| `!important` em `compact.css` | 145 |
| Cores hex em `visual-system.css` | 150 |
| Cores hex em todos os CSS | 503 |
| Cores hex em templates | 564 |
| Atributos `style=` em templates | 939 |
| Ocorrências de `9px` em templates/CSS | 67 |
| Ocorrências de `10px` em templates/CSS | 311 |
| Ocorrências de `11px` em templates/CSS | 143 |
| Tags `<table>` | 29 |
| Ocorrências de `table-responsive` | 23 |
| Arquivos CSS ativos | 11 |

Os valores confirmam a tendência descrita no relatório, mas mostram que a quantidade de estilos inline é superior à estimativa inicial. Os números devem ser usados como baseline de comparação, não como meta de remoção cega.

## Conflitos confirmados

### Cascata e temas

`visual-system.css` e `palette03-final.css` possuem regras globais sobre a mesma sidebar, botões, alertas, modais, tabelas e autenticação. A sidebar, por exemplo, recebe regras em `main.css`, `theme.css`, `visual-system.css` e `palette03-final.css`. `color-themes.css` fornece os tokens das seis paletas, mas camadas posteriores ainda impõem valores e especificidade próprios.

Existem cores hardcoded em `templates/base.html`, especialmente nos botões da navbar, incluindo `#1a1a1a`, `#333` e `#a01f25`. Essas regras são carregadas antes dos tokens finais, mas usam `!important` e permanecem como dívida técnica. As telas públicas ainda possuem fundos, textos e botões definidos diretamente em estilos inline.

### Tipografia

Foram confirmadas pelo menos cinco famílias ou estratégias concorrentes: Segoe UI, Inter, Source Sans 3, Fraunces e monospace genérico. O layout autenticado importa Segoe UI, o CSS base usa Inter, `visual-system.css` usa Source Sans 3 e Fraunces, e as telas públicas usam Inter. Há também uso direto de `font-family: monospace` em identificadores e atalhos.

### Responsividade

A largura da sidebar aparece como 220px em `main.css` e `theme.css`, 240px em `visual-system.css` e 230px com `!important` em `mobile.css`. Foram confirmados dois controles distintos de navegação: `.hamburger-menu` no corpo da sidebar e `#mobile-menu-btn` no layout mobile. O JavaScript também possui lógica para ambos, portanto a consolidação deve ser feita com cuidado.

Existem 29 tabelas e apenas 23 ocorrências de `table-responsive`. O baseline não assume que cada ocorrência corresponda a uma tabela única; a etapa seguinte deverá mapear os seis casos restantes por template.

### Tema claro/escuro

`static/js/theme-toggle.js` existe e cria ou controla um botão `#theme-toggle-btn`, grava `registrofacil-theme` no `localStorage` e aplica `data-theme="light|dark"` no elemento HTML. Nenhum template carrega esse script e não foram localizadas regras CSS reais para `[data-theme="dark"]` ou `[data-theme="light"]`. O mecanismo está, portanto, presente no código, mas não integrado ao fluxo visual atual.

## Pontos de atenção para a próxima etapa

A remoção direta de `palette03-final.css` não é segura neste momento, pois ele contém a proteção final que vence estilos legados. A estratégia correta é migrar os tokens e componentes para uma camada base consolidada, validar as seis paletas e somente então retirar o arquivo ou transformá-lo em uma camada de compatibilidade vazia.

A primeira correção estrutural deve ser a definição da arquitetura alvo e dos tokens semânticos. Em seguida, os hardcodes e estilos inline devem ser migrados por grupos funcionais. A limpeza de `!important`, a padronização tipográfica e a revisão responsiva dependem dessa ordem.

## Critérios de aceite da Etapa 1

O inventário foi concluído sem alteração funcional. A ordem de carregamento, os arquivos concorrentes, as métricas de especificidade, as famílias tipográficas, as larguras da sidebar, os controles mobile, as tabelas e o toggle claro/escuro foram identificados e registrados. Os arquivos de apoio são `docs/visual-baseline-inventory.txt`, `docs/visual-baseline-metrics.txt` e `docs/visual-baseline-theme-toggle.txt`.
