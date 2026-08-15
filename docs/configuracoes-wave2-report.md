# Segunda onda de refatoração — `configuracoes.html`

## Resultado

A segunda onda extraiu estilos estáticos de painéis, formulários, controles de backup e estabelecimento para classes semânticas no `visual-system.css`. A migração preservou expressões Jinja, dados de status, cores de swatches, visibilidade condicional e handlers de hover necessários ao comportamento existente.

| Indicador | Antes | Depois | Redução |
|---|---:|---:|---:|
| `style=` em `configuracoes.html` | 124 | 46 | 78 |
| `style=` em todos os templates | 880 | 802 | 78 |
| `!important` em `visual-system.css` | 348 | 348 | 0 |
| Temas semânticos | 6 | 6 | preservados |
| Tokens obrigatórios | 50 | 50 | preservados |
| Testes automatizados | 60 | 60 | aprovados |

## Classes extraídas

Foram adicionadas classes para o corpo compacto de cards, layouts flexíveis, campos de caminho, botões de navegação de diretório, caminhos gerenciados, selects e horários, estados condicionais, corpo de backup automático, cabeçalhos de switches, logo, registro da empresa, ações alinhadas à direita e modais.

## Valores preservados

Os estilos dependentes de dados continuam inline ou condicionais por segurança. Isso inclui `{{ s.hex_color }}`, estados ativo/inativo dos status, `display` condicionado por provedor SFTP, ativação do backup automático e frequência semanal/mensal, além do cursor dependente do perfil administrativo. Os handlers de hover do botão de diretório também foram preservados nesta passada.

## Pendências controladas

Restam 46 estilos inline em `configuracoes.html`. Os principais grupos remanescentes são swatches com cores de apresentação, displays condicionais de SFTP e frequência de backup, cursor dependente do perfil e pequenos estilos dinâmicos. Esses casos foram mantidos deliberadamente para não quebrar a lógica de dados e os handlers existentes. A próxima onda pode tratar propriedades dinâmicas com classes e atributos de dados, se houver benefício comprovado.

A validação semântica confirmou os seis temas e 50 tokens obrigatórios. A suíte automatizada terminou com 60 testes passando, não foram encontrados atributos `class` duplicados e `git diff --check` permaneceu limpo. O total global de `!important` permaneceu em 568, e o `visual-system.css` permaneceu em 348, pois não foram removidas prioridades globais sem migração completa dos componentes dependentes. Esta onda ainda não foi commitada ou publicada.
