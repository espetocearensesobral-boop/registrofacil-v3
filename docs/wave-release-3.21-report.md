# Nova onda visual — preparação da release 3.21.0

## Resultado executivo

A nova rodada corrigiu os pontos mais objetivos do relatório de acompanhamento sem alterar a identidade institucional dos seis temas. A intervenção concentrou-se em reduzir a dependência de `!important`, eliminar a duplicidade semântica dos botões, elevar a microtipografia da interface, consolidar famílias de fonte, estruturar as larguras da sidebar e completar o contrato de dark mode.

## Métricas antes e depois

| Indicador | Antes da onda | Depois da onda | Resultado |
|---|---:|---:|---|
| `!important` em CSS | 684 | 568 | Redução de 116 ocorrências. |
| `!important` em `visual-system.css` | 464 | 348 | Redução de 116 ocorrências. |
| Fontes de UI abaixo de 12px | 173 ocorrências auditadas | 0 fora dos relatórios de impressão | Corrigido na interface operacional. |
| Alias `.nav-btn-gold` | Presente | 0 ocorrências | Substituído por `.nav-btn-primary`. |
| Famílias `Inter`/`Segoe UI` na UI ativa | Presentes | Removidas | Source Sans 3 centralizada. |
| Largura estrutural da sidebar | Valores concorrentes | Tokens de 15rem e 4rem | Expandida e colapsada consolidadas. |
| Dark mode semântico | Sem seletores CSS | Contrato `[data-theme="dark"]` presente | Superfícies, texto, bordas e feedback cobertos. |
| Paleta 05 | Sidebar `#FFFFFF` | Sidebar `#F1F4F3` | Tema claro institucional equilibrado. |

As fontes menores remanescentes pertencem exclusivamente aos templates de impressão, que foram preservados para não alterar a paginação dos documentos gerados. A contagem ampla de `width` também não deve ser usada como métrica única da sidebar, pois inclui dimensões de controles e componentes internos.

## Validação

A validação semântica confirmou 6 temas e 50 tokens obrigatórios. A suíte automatizada terminou com 60 testes passando. Python, `accessibility.js` e `theme-toggle.js` foram verificados sintaticamente, e `git diff --check` não apontou erros.

No navegador, a Paleta 05 clara computou fundo de página `rgb(245, 241, 232)`, card branco, texto `rgb(36, 48, 56)` e sidebar `#F1F4F3`. Em dark mode, computou fundo `rgb(17, 24, 28)`, card `#1A2429`, texto claro e contraste secundário elevado. O seletor CSS de dark mode foi detectado na folha carregada.

## Estado da release

A configuração central foi atualizada para **3.21.0**. Os testes de atualização foram ajustados para tratar **3.22.0** como próxima versão candidata. Nenhum commit, push ou merge da nova onda foi realizado ainda; a release 3.20.0 permanece como referência remota e a árvore local contém apenas as alterações desta nova onda, os relatórios e a documentação de validação.

## Próxima decisão

Antes de publicar, deve ser feita uma revisão final do diff e uma inspeção visual das telas autenticadas em cinco larguras. Depois disso, a sequência recomendada é criar o commit da 3.21.0, publicar a branch e aguardar autorização explícita para merge, repetindo o procedimento adotado na release anterior.
