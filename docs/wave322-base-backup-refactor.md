# Onda v3.22 — refatoração de `base.html` e `backup.html`

## Resultado

A primeira onda de refatoração converteu os estilos estáticos dos templates globais e da tela de backups em classes semânticas no `visual-system.css`. Foram preservados os valores dinâmicos, como nomes de arquivos, cores provenientes de processos e dados de status.

| Indicador | Antes | Depois | Redução |
|---|---:|---:|---:|
| `style=` em `base.html` | 9 | 0 | 9 |
| `style=` em `backup.html` | 11 | 0 | 11 |
| `style=` em todos os templates | 938 | 880 | 58 |
| `!important` no `visual-system.css` | 349 durante a onda | 348 | 1 |

A diferença entre a redução de 20 estilos nos dois templates e a redução global de 58 ocorre porque regras estáticas compartilhadas e trechos correlatos também foram normalizados durante a migração. A contagem de `!important` foi reduzida somente onde a prioridade deixou de ser necessária; as prioridades globais restantes continuam protegendo componentes ainda não migrados.

## Classes adicionadas

Foram criadas classes para o perfil do shell, modais de exclusão, busca global, toast, modal de atalhos, logo, ações de backup, tabela de backups, caminho do banco, estados vazios e indicadores de status. Todas usam tokens semânticos institucionais, incluindo fontes, superfícies, bordas, ações, feedback e raios.

## Validação

A validação semântica confirmou 6 temas e 50 tokens obrigatórios. A suíte automatizada terminou com 60 testes passando. A checagem de diff não encontrou erros, não foram encontrados atributos `class` duplicados nos templates-alvo e os valores dinâmicos foram preservados.

## Limite seguro

A próxima redução de `!important` não deve ser feita por remoção global. Ainda existem regras que cobrem templates fora de `base.html` e `backup.html`, além de estilos inline restantes em 44 templates. O próximo grupo recomendado é migrar componentes de tabelas e cards de `processos/visualizar.html`, `visualizar.html` e `permissoes_usuario.html`, sempre separando propriedades estáticas de valores gerados pelo banco.
