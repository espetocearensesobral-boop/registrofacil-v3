# Notas de QA visual

## 22/08/2026

### Dashboard — desktop

A tela inicial autenticada carregou com shell lateral, topbar, ações primárias, quatro KPIs, cartões de processos recentes e prazos críticos, três áreas de gráficos e leitura operacional. A composição manteve a hierarquia visual, contrastes e estados vazios legíveis.

### Métricas — desktop

A rota `/dashboard/metricas` carregou sem erros visíveis. A barra de contexto, tabs, KPIs, cartões de gráficos e comparativo aparecem em sequência coerente. Os estados sem dados foram tratados com mensagem e ícone, e a estrutura expõe `role=tab`, `tabpanel`, `aria-controls` e `aria-selected`.

### Backup — desktop

A rota `/backup/` carregou com três KPIs, cartão de última execução, ações de geração/teste/reparo, caminho do banco e estado vazio de backups. As ações críticas ficaram agrupadas e os textos de estado permanecem claros.

### Perfil — desktop

A rota `/perfil/` carregou com editor principal de dados e senha, ações no rodapé, cartão de aparência e informações da conta. Os rótulos aparecem em caixa alta com contraste consistente e os controles de senha mantêm rótulos ARIA.

### Verificação estrutural das métricas

A inspeção do DOM após a correção confirmou que `tab-visao-geral` e `tab-equipe` ficam com `hidden=true`, `aria-hidden=true`, `display:none` e dimensões zero enquanto `tab-meu-desempenho` está ativo. Isso preserva o comportamento de uma única aba visível, mesmo quando a captura anotada do navegador reteve um quadro lateral transitório.

### Atividades e auditoria — rota real

A URL legada `/atividades/historico` redireciona intencionalmente para `/configuracoes/?tab=atividades`, conforme o blueprint de compatibilidade. A tela efetiva exibida é o painel unificado de eventos, com filtro, legenda de fontes, tabela e botão de detalhe.

### Configurações / Status — desktop

A aba `/configuracoes/?tab=status` carregou com tabs compactas, formulário de inclusão com seletor de cor, tabela de status cadastrados e ações por registro. O conteúdo utiliza a superfície de configurações e mantém a leitura dos estados Ativo/Inativo.
