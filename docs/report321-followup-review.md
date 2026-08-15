# Revisão do relatório de acompanhamento v3.21

## Conclusão

O relatório está correto quanto aos avanços funcionais: dark mode presente, Paleta 05 corrigida, alias `.nav-btn-gold` removido, tipografia operacional sem ocorrências abaixo de 12px pelo padrão auditado e larguras estruturais da sidebar centralizadas em tokens.

A principal ressalva é a métrica de `!important`. Na árvore local correspondente ao commit publicado `864a0b6`, a contagem reproduzível é de **568 ocorrências em CSS**, sendo **348 em `static/css/visual-system.css`**. Portanto, a estimativa de “200+ apenas no visual-system.css” é direcionalmente correta, mas subestima o valor exato atual. A meta de menos de 50 deve ser tratada como objetivo de várias ondas, não como uma remoção única.

## Métricas confirmadas

| Indicador | Estado atual |
|---|---:|
| Versão central | 3.21.0 |
| `!important` em CSS | 568 |
| `!important` no visual-system | 348 |
| Atributos `style=` em templates | 938 |
| Templates com `style=` | 46 |
| Fontes de UI abaixo de 12px | 0 fora de relatórios de impressão |
| Menções de `nav-btn-gold` | 0 |
| Regras dark mode | 1 bloco semântico abrangente |
| Temas validados anteriormente | 6 |
| Suíte automatizada | 60 testes passando |

A contagem de `style=` é o dado mais relevante para explicar a cascata atual: existem 938 atributos inline distribuídos em 46 templates. Nem todos são conflitos de cor — muitos são espaçamento, dimensões de tabelas, dados dinâmicos ou estilos de impressão — portanto a remoção deve ser feita por grupos semânticos e não por substituição cega.

## Primeiro grupo recomendado

A primeira onda de remoção deve começar por **`templates/base.html` e `templates/backup.html`**, priorizando modais, botões de ações e cabeçalhos de tabela que usam valores semânticos já disponíveis nos tokens. Esses trechos são compartilhados ou visualmente concentrados, têm baixo risco de regra dinâmica e permitem medir a queda de `!important` sem alterar a estrutura de dados.

Os estilos inline que carregam valores dinâmicos, como cores vindas de `processo.hex_color`, devem permanecer inline ou migrar para propriedades customizadas sanitizadas em uma etapa específica. Não devem ser removidos junto com estilos estáticos.

## Recomendação

A próxima onda deve manter a release 3.21.0 intacta e criar uma branch ou commit separado para a v3.22. O trabalho deve seguir quatro ciclos: converter estilos estáticos dos modais e botões em classes; remover os `!important` correspondentes; validar os seis temas e os 60 testes; e só então avançar para tabelas, cards e telas de cadastro. A meta intermediária recomendada é reduzir o `visual-system.css` de 348 para menos de 250 ocorrências, preservando a aparência e os contratos funcionais.
