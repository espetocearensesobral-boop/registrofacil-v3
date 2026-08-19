# Auditoria do motor de logs — Registro Fácil

**Data:** 19/08/2026  
**Versão analisada:** 3.28.43  
**Escopo:** logger de arquivos, auditoria persistente, Histórico de Atividades, segurança, scheduler, retenção e desempenho.

## Conclusão executiva

O Registro Fácil possui uma base de logging funcional, mas atualmente mantém **quatro camadas parcialmente sobrepostas**: arquivos por domínio, logger legado `registrofacil_app`, tabela operacional `logs` e tabelas específicas de segurança/auditoria. A infraestrutura de arquivos já está segmentada, mas a maioria do código ainda importa `from utils.logger import logger`. A auditoria estática encontrou **36 arquivos usando o import legado**, contra somente **4 arquivos usando diretamente loggers de domínio**, e aproximadamente **511 ocorrências combinadas de imports/chamadas de logging** no código.

A recomendação não é apagar os logs existentes nem transformar tudo em uma única tabela. O desenho mais seguro é **unificar o motor de emissão e o formato**, mantendo destinos especializados quando há necessidade operacional ou de segurança.

> O problema principal não é existir mais de um destino; é o mesmo evento poder passar por caminhos diferentes, receber formatos diferentes, ser duplicado em arquivo e banco ou simplesmente ser descartado por listas de prefixos.

## Arquitetura atual

| Camada | Destino | Uso atual | Avaliação |
|---|---|---|---|
| Logger por domínio | `logs/auth`, `logs/operacional`, `logs/sistema`, `logs/manutencao` | Rotação diária e retenção aproximada de 90 dias | Base correta, mas subutilizada pelos módulos legados. |
| Logger legado | `registrofacil_app` apontando para `logs/operacional` | Compatibilidade com dezenas de módulos | Deve ser mantido temporariamente, mas não como caminho preferencial. |
| Auditoria operacional | Tabela SQLite `logs` | Cadastro, edição, exclusão, backups e algumas configurações | Útil para Histórico de Atividades, mas depende de allowlist de ações. |
| Auditoria administrativa | Tabela `auditoria_admin` | Alteração de role, senha, status, permissões e justificativas | Deve permanecer separada e com acesso restrito. |
| Segurança | `tentativas_acesso_nao_autorizado`, `login_attempts` e arquivo `auth.log` | Falhas de login, acessos bloqueados e tentativas administrativas | Necessária, mas há duplicidade parcial entre banco e arquivo. |
| Presença | Tabela `user_presence` | Último heartbeat e IP observado | Não é log histórico; deve permanecer como estado operacional atual. |

## Pontos positivos

A segregação por domínio facilita diagnóstico e evita que autenticação, manutenção e operação fiquem misturadas em um único arquivo. O `RequestContextFilter` injeta usuário e IP automaticamente dentro do contexto Flask, e o código permite sobrescrever esses dados com `extra` em tarefas de background. A rotação diária e a limpeza automática de arquivos antigos já existem, e os índices de `logs`, `auditoria_admin` e tentativas de acesso cobrem as consultas mais importantes.

A auditoria administrativa também captura justificativa, campo alterado, valores anterior e novo, IP, user agent e usuário afetado. Essa trilha é mais rica que um log operacional comum e não deve ser reduzida à tabela `logs`.

## Problemas identificados

### 1. Migração incompleta para os domínios

O logger legado ainda é utilizado por 36 arquivos, incluindo autenticação, banco, processos, usuários, backup, scheduler, rotas e configurações. Em contrapartida, os loggers de domínio são usados diretamente em poucos pontos. Isso faz com que mensagens de banco e manutenção caiam em `operacional.log`, apesar de já existirem `sistema.log` e `manutencao.log`.

O caso mais evidente é `utils/scheduler.py`: ele importa `manutencao_logger`, mas a maior parte das mensagens de backup, ZIP, temporários e SFTP continua usando `logger`. A mensagem acaba no logger legado/operacional em vez de manutenção.

**Melhoria:** migrar progressivamente por módulo, começando por `utils/scheduler.py`, `data/backup.py`, `data/database.py`, `data/migrations.py` e `routes/backup.py`.

### 2. Logger legado cria compatibilidade, mas também confusão

`utils/logger.py` constrói `registrofacil_app` apontando para `logs/operacional` e mantém aliases de segurança e domínios. Isso evita quebra imediata, mas torna difícil saber pelo nome do logger qual é a classificação real do evento.

**Melhoria:** manter o logger legado apenas como camada de compatibilidade por uma versão de transição. Adicionar um aviso de desenvolvimento quando um módulo novo importar `logger` genérico e definir uma data para remover o caminho legado.

### 3. Allowlist frágil em `data/logging.py`

A função `gravar_log` decide o destino usando conjuntos de ações exatas e prefixos como `Cadastrou`, `Editou` e `Exclu`. Uma nova ação pode não ser enviada para nenhum destino sem erro explícito. Além disso, locks são descartados silenciosamente por `ACOES_IGNORADAS`, o que elimina rastreabilidade quando há conflito de concorrência.

**Melhoria:** substituir a decisão por prefixos por um evento estruturado com categoria explícita, por exemplo `domain='operacional'`, `event='process.updated'`, `severity='info'` e `audit=True/False`. Eventos de lock podem ser `debug` ou métricas agregadas, mas falhas de lock devem permanecer registradas em nível `warning`.

### 4. Duplicidade entre arquivo e banco sem identificador comum

Login, logout, falhas de autenticação e algumas ações administrativas podem aparecer em arquivo e em banco. A duplicidade pode ser desejada para segurança, mas atualmente não existe um `event_id` ou `correlation_id` compartilhado que permita comprovar que duas entradas são o mesmo evento.

`gravar_auditoria_admin` grava na tabela `auditoria_admin` e depois emite outro `logger.info`. `gravar_tentativa_nao_autorizada` grava em banco e também escreve em `auth.log`. Isso deve ser documentado como duplicação intencional ou reduzido.

**Melhoria:** gerar um identificador de evento único e incluir o mesmo ID no arquivo e na tabela quando houver dupla persistência. O arquivo deve ser o fallback de segurança; a tabela deve ser a fonte consultável para a interface.

### 5. Histórico de Atividades não representa toda a atividade do sistema

A tela `Histórico de Atividades` consulta exclusivamente a tabela `logs`. Ela não apresenta `auditoria_admin`, `tentativas_acesso_nao_autorizado`, `login_attempts` ou `user_presence`. Portanto, o administrador pode interpretar o histórico como completo, embora ele mostre apenas os eventos selecionados por `gravar_log`.

**Melhoria:** manter a tela operacional, mas nomeá-la claramente como **Histórico Operacional**. Criar, futuramente, uma tela administrativa separada para auditoria e segurança, ou uma view unificada somente para leitura que preserve a origem do evento.

### 6. Retenção não é uniforme entre as trilhas

Os arquivos possuem limpeza automática por idade. As tabelas `logs`, `auditoria_admin`, `tentativas_acesso_nao_autorizado` e `login_attempts` possuem índices, mas a auditoria revisada não evidenciou uma política equivalente de expurgo ou arquivamento para os registros persistentes.

**Melhoria:** definir retenção por classe. Uma política inicial possível é: operacional conforme volume; segurança e auditoria por período maior; presença sem histórico, mantendo somente o estado atual; tentativas de login com retenção limitada e anonimização quando aplicável. A política deve ser configurável e registrada em documentação.

### 7. Dados sensíveis em mensagens

Há mensagens que incluem e-mail, IP, nome de usuário, caminho completo do banco, caminho de backup, host SMTP e detalhes de SFTP. Algumas informações são úteis para diagnóstico, mas devem ser protegidas por nível e destino. O logger de configuração de e-mail já evita imprimir a senha, o que é positivo.

**Melhoria:** aplicar mascaramento para e-mail, IP externo, host remoto e caminhos sensíveis em nível `INFO`; manter o detalhe completo somente em `DEBUG` ou auditoria protegida. Nunca registrar senha, token, chave, cookie ou conteúdo completo de requisição.

### 8. Performance e volume

O baseline de estresse mostrou que o sistema funciona bem com 10 usuários, mas as mensagens de processo e histórico em nível `INFO`/`DEBUG` produzem volume alto. Durante o teste local, o `operacional.log` cresceu muito mais que os outros domínios, e o Waitress apresentou mensagens de fila em carga alta.

**Melhoria:** reduzir logs de sucesso repetitivos de processos e histórico para `DEBUG`, manter `INFO` para eventos de negócio importantes e `WARNING/ERROR` para problemas. Adicionar rotação também por tamanho, por exemplo 25–50 MB, além da rotação diária.

## Arquitetura recomendada

A arquitetura-alvo deve possuir um **único ponto de emissão estruturada** e múltiplos destinos controlados:

```text
Evento da aplicação
        |
        v
AuditEvent / LogEvent
(domain, event, severity, user_id, ip, request_id, entity_id, details)
        |
        +--> arquivo diário por domínio
        +--> tabela logs somente quando audit=True
        +--> tabela auditoria_admin para ações administrativas
        +--> tabela security_events para segurança, se necessário
```

A unificação deve ocorrer no contrato, não necessariamente em um único arquivo ou tabela. O evento deve possuir `event_id`, timestamp UTC/local documentado, domínio, ação estável, nível, usuário, IP, request/correlation ID, entidade afetada e detalhes sanitizados.

## Plano priorizado

| Prioridade | Ação | Motivo |
|---|---|---|
| P0 | Corrigir o isolamento de logs do harness de estresse | Evita que testes futuros contaminem logs reais. A correção foi aplicada localmente no harness e deve ser preservada no próximo commit. |
| P1 | Migrar scheduler e backup para `manutencao_logger` | Corrige classificação e reduz ruído em `operacional.log`. |
| P1 | Migrar banco, schema, migrations e FTS para `sistema_logger` | Separa diagnóstico técnico de atividade de negócio. |
| P1 | Definir política de níveis: INFO negócio, DEBUG diagnóstico, WARNING conflito, ERROR falha | Reduz volume e melhora leitura. |
| P1 | Adicionar rotação por tamanho e validar retenção das tabelas | Evita crescimento silencioso em produção. |
| P1 | Diferenciar “Histórico Operacional” de “Auditoria e Segurança” | Evita que a interface sugira cobertura incompleta. |
| P2 | Criar `event_id`/`correlation_id` comum a arquivo e banco | Permite reconciliar duplicidades intencionais. |
| P2 | Substituir allowlists de prefixos por eventos estruturados | Torna o sistema extensível e evita eventos descartados silenciosamente. |
| P2 | Criar view administrativa unificada somente leitura | Facilita investigação sem misturar semântica operacional e de segurança. |
| P3 | Preparar exportação/arquivamento de auditoria | Útil quando houver exigência de retenção longa ou ambiente com múltiplas unidades. |

## Decisão recomendada

Não recomendo remover a segregação nem apagar as tabelas específicas. Recomendo **unificar o motor e o contrato de eventos**, preservar `auditoria_admin` e as trilhas de segurança, manter `logs` para operação e migrar os módulos restantes para os loggers de domínio. A primeira aplicação deve ser pequena e segura: migrar scheduler/backup, sistema/banco e reduzir o nível de logs repetitivos. Depois, com testes, pode-se introduzir `event_id` e a nova tela de auditoria.

A auditoria não recomenda alterar a lógica de consulta, filtros, paginação, impressão, PDF, Excel, permissões ou hardening de segurança nesta etapa.


## Estado pós-implementação — versão 3.28.44

A refatoração descrita neste documento foi aplicada e validada na release 3.28.44. O sistema passou a usar o contrato estruturado de eventos em `utils/log_events.py`, com `event_id`, `request_id`, domínio, tipo de evento, entidade, severidade, detalhes sanitizados e mascaramento de segredos. Os módulos executáveis foram migrados para os loggers de domínio; a auditoria estática final não encontrou importações do logger genérico legado fora da fachada de compatibilidade.

A tabela `logs` agora mantém os campos estruturados e índices correspondentes. As trilhas `auditoria_admin`, `tentativas_acesso_nao_autorizado` e `login_attempts` preservam sua separação semântica e receberam correlação por identificadores. O **Histórico Operacional** permanece separado da tela **Auditoria e Segurança**, que reúne ações administrativas e bloqueios de segurança somente para perfis autorizados.

A rotação dos arquivos combina limite de tamanho de 25 MB e mudança de dia, com retenção de arquivos configurável. A retenção persistida usa 365 dias para operação e 730 dias para segurança, mantendo o expurgo de segurança desativado por padrão. O harness de estresse continua isolado dos logs reais e a suíte local final cobre sanitização, rotação, schema, persistência, retenção e a rota administrativa.

A validação final desta entrega deve ser repetida no ambiente Windows antes da compilação do instalador, especialmente o build com PyInstaller, o firewall restrito à sub-rede local, o autostart sem navegador e o acesso simultâneo pelos terminais.
