# Revisão do relatório 4c2f38b — Registro Fácil v3.21

## Validação do estado publicado

O relatório foi confrontado com o commit publicado `4c2f38b`. As métricas principais foram confirmadas: 568 ocorrências de `!important` no CSS, 348 no `visual-system.css`, 880 atributos `style=` em 44 templates e 124 estilos inline em `templates/configuracoes.html`.

| Indicador | Estado confirmado |
|---|---:|
| Commit analisado | `4c2f38b` |
| Versão central | 3.21.0 |
| `!important` total | 568 |
| `!important` no visual-system | 348 |
| Atributos `style=` nos templates | 880 |
| Templates com inline | 44 |
| Inline em `configuracoes.html` | 124 |
| Inline em `permissoes_usuario.html` | 57 |
| Inline em cada listagem de titulares, representantes e apresentantes | 54 |
| Inline em cada tela de visualização | 46 |

A tabela do relatório que estima contagens por folha deve ser lida como aproximação, pois as linhas de `color-themes.css`, `mobile.css` e outras folhas não foram recalculadas individualmente nessa auditoria. O total global de 568 e o valor do `visual-system.css` foram medidos diretamente.

## Diagnóstico de configuracoes.html

A prioridade de `configuracoes.html` está correta. O arquivo possui um bloco local de CSS já relativamente organizado com classes `.cfg-*`, mas ainda mantém 124 estilos inline em cinco grupos principais: espaçamento de cards e formulários; swatches com cores literais; controles de backup e frequência; painel de estabelecimento e logo; e modais de edição.

Nem todos os 124 casos devem ser removidos de uma vez. Valores de swatches como `background:#0d6efd` são dados de apresentação associados à escolha de uma cor e devem migrar para propriedades customizadas ou permanecer como valor controlado. Estados de frequência com `display:block/none` dependem de Jinja e devem ser convertidos para classes condicionais. Dimensões estáticas, alinhamentos, tipografia e bordas podem migrar diretamente para classes `.cfg-*`.

## Segunda onda recomendada

A refatoração deve começar por quatro subgrupos: o corpo e o cabeçalho do painel principal; formulários de status e serviços; controles de backup; e o bloco de estabelecimento/logo. A meta segura é retirar entre 70 e 90 atributos inline na primeira passada, sem alterar os estilos dinâmicos de swatches, visibilidade condicional e dados de empresa.

Somente depois de validar os seis temas e os 60 testes deve-se tratar os modais de edição e os blocos de permissões. A meta de menos de 50 inline em `configuracoes.html` é plausível, mas deve ser alcançada em duas passadas para manter o risco baixo.

## Próximo passo

A próxima execução deve criar classes semânticas adicionais no `visual-system.css` ou em uma folha específica de configurações, migrar os estilos estáticos de `configuracoes.html` e medir novamente a cascata. A release publicada permanece intacta até a autorização explícita para aplicar essa segunda onda.
