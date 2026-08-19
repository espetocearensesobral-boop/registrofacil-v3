# Diagnóstico confirmado — Configurações

A causa raiz da tela estreita não era a classe `.cfg-settings-rebuild` nem a tabela isoladamente. O partial `templates/_config_about_panel.html` não possuía a abertura do contêiner `.cfg-panel`, mas continha o fechamento final `</div>`. Esse HTML malformado fazia o navegador reconstruir a árvore DOM e retirava o `footer` de dentro de `#page-content-wrapper`, transformando-o em irmão flexível de `#page-content-wrapper` dentro de `#wrapper`.

Antes da correção, no navegador, `#page-content-wrapper` media aproximadamente 439px de largura em uma área útil de 1265px, enquanto `#wrapper` media 1265px. O conteúdo de Configurações ficava comprimido e a tabela criava overflow horizontal.

A correção aplicada foi adicionar no início do partial:

```html
<div class="cfg-panel{% if active_tab == 'sobre' %} active{% endif %}" id="panel-sobre">
```

Após a correção, a prévia real do template passou a medir aproximadamente 1025px para `#page-content-wrapper` e `#main-content`, 993px para o contêiner de Configurações e o `scrollWidth` do documento ficou igual à largura útil (1265px), sem overflow horizontal global. A tabela de Status passou a usar a largura disponível.

Também foi removido o bloco legado `.cfg-settings-shell` de `static/css/layout-standard.css` e foram adicionados rótulos `data-label` com modo de cartões no breakpoint móvel para Status e Tipos de Serviço.
## Validação adicional

Na prévia no navegador, a aba Sobre ficou ativa de forma exclusiva (`activeCount: 1`), com `panel-sobre` visível e todos os demais painéis ocultos. O rodapé voltou a ser filho direto de `#page-content-wrapper`. A largura calculada de `#main-content` permaneceu em aproximadamente 1025px, com `scrollWidth` do documento igual a 1265px, confirmando que a navegação da aba Sobre não reintroduz o problema.
## Validação móvel

A regra global `#page-content-wrapper .table-responsive > table { min-width: 640px; }` também participava do overflow em telas estreitas. No breakpoint móvel, a reconstrução agora força `min-width: 0 !important`, `width: 100%` e converte a tabela em cartões empilhados.

No viewport automatizado de 390px, a largura útil foi 375px, o `.table-responsive` e a tabela passaram a medir 343px, cada célula passou a medir aproximadamente 322px e o `scrollWidth` do documento permaneceu 375px. A captura móvel final mostrou os valores de Cor, Processos e Situação visíveis, com as ações alinhadas no canto direito e sem corte horizontal.
