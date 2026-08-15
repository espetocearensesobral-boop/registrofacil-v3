# Revisão do relatório visual da release 3.20.0

## Conclusão executiva

O relatório está tecnicamente consistente nos principais alertas e confirma que a release 3.20.0 avançou na consolidação dos temas, mas ainda carrega dívida técnica relevante na cascata CSS, na escala tipográfica, na definição de largura da sidebar e na convivência de famílias tipográficas legadas. A próxima rodada deve ser tratada como uma evolução de manutenção e acessibilidade, não como uma nova troca de identidade visual.

## Métricas reproduzidas no repositório

| Indicador | Valor reproduzido | Leitura |
|---|---:|---|
| Arquivos CSS ativos | 7 | Confirmado. |
| `!important` em CSS | 684 | Confirmado. |
| `!important` em `visual-system.css` | 464 | Confirmado e prioritário. |
| Fontes menores que 12px em templates | 173 ocorrências pelo padrão auditado | Confirmado em ordem de grandeza; deve ser revisado por contexto, pois nem todo texto auxiliar tem o mesmo impacto. |
| `.nav-btn-gold` e `.nav-btn-primary` | 16 ocorrências de cada | Confirmado. |
| Sidebar da Paleta 05 | `#FFFFFF` | Confirmado. |
| Famílias legadas `Inter` e `Segoe UI` | 11 ocorrências de cada | Confirmado. |
| Seletores dark mode no CSS semântico | 0 | Confirmado; o script alterna `data-theme`, mas não existe contrato CSS correspondente. |

A contagem ampla de valores `width` não deve ser usada isoladamente para concluir que todos pertencem à sidebar, pois inclui breakpoints, larguras de modais, controles e elementos internos. A consolidação deverá separar explicitamente a largura estrutural da sidebar, a largura colapsada, a largura do drawer mobile e as dimensões internas dos seus controles.

## Priorização proposta

### Etapa 1 — Cascata e métricas de base

Mapear os 464 usos de `!important` por componente, remover duplicidades e preservar apenas exceções justificadas por Bootstrap ou por estilos inline ainda não migrados. O objetivo inicial deve ser reduzir conflitos sem alterar a identidade visual, com validação visual após cada grupo.

### Etapa 2 — Tipografia acessível

Substituir fontes de 9px, 10px e 11px por tokens semânticos, começando por `configuracoes.html`, `dashboard.html` e `perfil.html`. Textos auxiliares podem usar o token mínimo de 12px, enquanto labels, badges e conteúdo operacional devem partir de 14px quando houver espaço disponível. A revisão deve remover `Inter` e `Segoe UI` das regras ativas e centralizar a família sans-serif em Source Sans 3.

### Etapa 3 — Sidebar e botões

Definir tokens distintos e explícitos para sidebar expandida, sidebar colapsada e drawer mobile, sem literais estruturais concorrentes. Em paralelo, substituir `.nav-btn-gold` por `.nav-btn-primary`, mantendo classes de intenção apenas quando houver diferença semântica real, como perigo ou ação secundária.

### Etapa 4 — Paleta 05 e dark mode

Trocar a sidebar branca pura da Paleta 05 por um tom claro institucional com borda e contraste equilibrados, preservando a proposta de tema claro. Em seguida, implementar o contrato `[data-theme="dark"]` para superfícies, textos, bordas, controles, feedback, sidebar e modais em todas as seis paletas, sem alterar a preferência de tema institucional do usuário.

### Etapa 5 — Validação e release 3.21.0

Executar a suíte automatizada, o validador dos 6 temas, auditoria de `!important`, contagem tipográfica, verificação de contraste, inspeção das cinco larguras responsivas e smoke test no navegador. Somente após essa etapa deverá ser criada a versão 3.21.0.

## Estado atual

Nenhuma correção da versão 3.21.0 foi aplicada com base apenas no relatório. A release 3.20.0 permanece preservada no commit `1addc4f`, e este documento registra a auditoria confirmatória que deve orientar a próxima execução.
