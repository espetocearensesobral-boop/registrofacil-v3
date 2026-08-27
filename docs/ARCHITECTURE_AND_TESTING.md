# Arquitetura e testes do RegistroFácil

**Versão documentada:** 3.19.0

## Visão geral

A camada de dados foi dividida no pacote `data/`, mantendo `models.py` como uma fachada de compatibilidade. As rotas existentes continuam importando símbolos legados sem conhecer a organização interna dos módulos.

| Componente | Responsabilidade |
| --- | --- |
| `models.py` | Reexporta funções e símbolos públicos para preservar imports existentes. |
| `data/schema.py` | Cria e verifica tabelas, índices, dados iniciais e campos de segurança. |
| `data/migrations.py` | Executa migrações versionadas do SQLite. |
| `data/database.py` | Centraliza conexões e execução de consultas. |
| `data/users.py` | Usuários, login, sessões, tokens e auditoria relacionada. |
| `data/processes.py` | Operações de processos e vínculos de domínio. |
| `data/registries.py` | CRUD de titulares e apresentantes, vínculos com processos e históricos. |
| `routes/` | Camada HTTP, autenticação, autorização e renderização. |
| `tests/` | Testes de domínio e testes HTTP com banco temporário. |

## Compatibilidade

Novos módulos devem ser importados diretamente dentro da camada de dados. Código de rota ou integração externa que ainda usa `models.py` pode continuar usando a fachada, evitando uma migração simultânea e reduzindo o risco de regressão.

A consulta de autenticação retorna `must_change_password` junto com os dados do usuário. Assim, o login consegue marcar `force_password_change` na sessão quando a conta inicial ou uma conta recém-resetada exige alteração de senha.

## Segurança operacional

Em produção, defina `REGISTROFACIL_ENV=production`, `INITIAL_ADMIN_PASSWORD` durante a primeira inicialização e uma `SECRET_KEY` persistente gerenciada pelo ambiente. Os cookies de sessão usam `HttpOnly`, `SameSite=Lax` e `Secure` por padrão em produção. `TRUST_PROXY_HEADERS` só deve ser habilitado quando a aplicação estiver atrás de um proxy reverso confiável que realmente remova ou reescreva os cabeçalhos encaminhados.

A aplicação não deve ser exposta diretamente à Internet sem TLS no proxy reverso. O proxy deve terminar HTTPS, encaminhar somente os cabeçalhos necessários e restringir o acesso ao servidor Flask. A flag `SESSION_COOKIE_SECURE` exige que o navegador receba a aplicação por HTTPS.

## Atualização de uma instalação existente

A versão 3.28.59 mantém o SQLite como banco compatível com a instalação anterior. A migração 014 consolida registros legados de Representantes em Apresentantes quando necessário e a migração 015 reconstrói a tabela `logs` para preservar os eventos quando um processo é excluído, convertendo referências históricas para `entity_id`. Na inicialização, `data/schema.py` verifica e cria colunas e tabelas ausentes de forma idempotente, enquanto `data/migrations.py` aplica as migrações de dados pendentes usando `PRAGMA user_version`. As migrações atuais levam bancos antigos até a versão de esquema 15 e preservam os registros existentes.

Antes de atualizar uma instalação com dados reais, faça uma cópia do arquivo `registrofacil.db`, da pasta de uploads e das chaves `.secret_key` e `.encryption_key` — ou forneça as mesmas chaves por variáveis de ambiente. A atualização deve ser executada primeiro em uma cópia de homologação. Não substitua as chaves ao migrar, pois isso pode impedir a leitura de dados criptografados e invalidar sessões existentes.

O procedimento recomendado é parar a versão antiga, copiar o banco para o ambiente de homologação, iniciar a versão 3.28.59 uma vez, verificar os logs de migração e executar um smoke test. Só depois dessa validação a cópia deve ser promovida para produção. A aplicação não deve ser iniciada sobre o banco de produção sem backup verificável.

Os prazos de retenção de arquivos podem ser ajustados por `REGISTROFACIL_LOG_RETENTION_DAYS` e `REGISTROFACIL_LOG_MAX_BYTES`. A retenção de logs persistidos usa `REGISTROFACIL_LOG_DB_RETENTION_DAYS` e `REGISTROFACIL_SECURITY_LOG_RETENTION_DAYS`; o expurgo de auditoria administrativa e segurança permanece desativado por padrão e só é habilitado com `REGISTROFACIL_PURGE_SECURITY_LOGS=true`.

## Instalação e testes

Crie um ambiente virtual, instale as dependências do projeto e execute a suíte a partir da raiz:

```bash
python -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
python -m pytest -q
```

Os testes HTTP usam um banco SQLite temporário e desabilitam o scheduler real. A cobertura inclui redirecionamento de usuários anônimos, validação CSRF, login, troca obrigatória de senha, invalidação de sessão após novo login e bloqueio de usuários comuns em rotas administrativas.

Para executar apenas os testes HTTP:

```bash
python -m pytest tests/test_http_auth.py tests/test_http_authorization.py -q
```

## Atualização coordenada do sistema

A primeira etapa do atualizador usa a tabela `configuracoes` para persistir o estado `system_update_state` em JSON. Isso evita criar uma tabela nova apenas para o controle inicial e mantém compatibilidade com bancos existentes.

Os estados principais são `idle`, `update_available`, `awaiting_confirmation`, `maintenance_pending`, `failed` e `ready`. O estado inclui versão de origem, versão de destino, progresso, mensagem, erro e indicação de recarga. Todos os terminais autenticados consultam `GET /api/system/update/status` e exibem o modo de manutenção quando há uma atualização em andamento.

As rotas administrativas são `POST /api/system/update/check`, `POST /api/system/update/confirm` e `POST /api/system/update/cancel`. Confirmação e cancelamento exigem autenticação administrativa e CSRF. O servidor retorna HTTP `423 Locked` para operações mutáveis enquanto o estado está em manutenção; bloquear apenas os botões do navegador não é suficiente.

Nesta etapa, `REGISTROFACIL_UPDATE_VERSION` pode ser usado em homologação para simular uma nova versão. O download, a conferência de assinatura, o backup, a troca atômica de diretórios e o reinício devem ser executados por um launcher externo, que será integrado em uma etapa posterior. O Flask não deve substituir os próprios arquivos enquanto estiver atendendo requisições.

## Canal externo de atualização pelo GitHub

O endereço do manifesto não fica fixo exclusivamente no código. Cada instalação pode possuir `DATA_DIR/update.ini`, copiado a partir de `update.ini.example`. O arquivo permite alterar `manifest_url`, `fallback_manifest_url`, `channel` e `timeout_seconds` sem recompilar o aplicativo.

A configuração usa como padrão um manifesto em um GitHub Release:

```ini
[update]
manifest_url = https://github.com/espetocearensesobral-boop/registrofacil-v3/releases/latest/download/manifest.json
fallback_manifest_url = https://raw.githubusercontent.com/espetocearensesobral-boop/registrofacil-v3/main/updates/manifest.json
channel = stable
timeout_seconds = 20
```

O Release é a fonte principal porque permite manter o endereço estável `releases/latest/download/manifest.json`, enquanto o nome do pacote pode variar por versão. O arquivo Raw fica como fallback caso o asset principal seja removido ou o endereço do Release seja alterado. A documentação do GitHub descreve esse padrão de link para o asset da release mais recente [1] e também disponibiliza `browser_download_url` para assets de releases via API [2].

O manifesto precisa conter pelo menos `version`, `package_url` e `sha256`. O sistema aceita somente URLs HTTPS e rejeita manifesto incompleto ou pacote sem hash SHA-256 válido. O exemplo está em `updates/manifest.example.json`.

As variáveis `REGISTROFACIL_UPDATE_CONFIG`, `REGISTROFACIL_UPDATE_MANIFEST_URL`, `REGISTROFACIL_UPDATE_FALLBACK_URL`, `REGISTROFACIL_UPDATE_CHANNEL` e `REGISTROFACIL_UPDATE_TIMEOUT` podem substituir o arquivo INI em ambientes automatizados.

### Referências

[1]: https://docs.github.com/en/repositories/releasing-projects-on-github/linking-to-releases "GitHub Docs — Linking to releases"
[2]: https://docs.github.com/en/rest/releases/assets "GitHub Docs — REST API endpoints for release assets"

## Launcher externo de releases

O módulo `data/update_launcher.py` prepara releases fora do diretório ativo. A estrutura usada é:

```text
DATA_DIR/updates/
├── downloads/
├── staging/
├── releases/
├── backups/
└── current.json
```

O launcher aceita somente pacotes HTTPS, exige SHA-256 com 64 caracteres hexadecimais, rejeita entradas ZIP com `..` ou caminhos absolutos e grava o ponteiro `current.json` com `os.replace`, evitando um arquivo parcialmente escrito.

Comandos disponíveis:

```bash
python -m data.update_launcher prepare caminho/manifest.json
python -m data.update_launcher backup
python -m data.update_launcher activate 3.19.0
```

O comando `prepare` somente baixa, valida e prepara a release. O comando `backup` copia banco, uploads e chaves. A ativação deve ser executada pelo supervisor externo depois que o Flask estiver bloqueando novas operações e o backup tiver sido confirmado. Ainda não é recomendado chamar `activate` diretamente a partir de uma requisição web.

## Integração com o worker externo

Depois da confirmação administrativa, o endpoint inicia `python -m data.update_worker` em um subprocesso separado. Durante testes, o subprocesso é desabilitado automaticamente para evitar efeitos colaterais. Em uma instalação empacotada, o comando pode ser substituído por `REGISTROFACIL_UPDATE_WORKER_COMMAND`.

O worker valida que o estado está em `maintenance_pending`, cria o backup, prepara a release, persiste o progresso e só ativa a versão quando existe `REGISTROFACIL_RESTART_COMMAND`. Sem esse comando, o estado fica em `ready_to_restart`, mantendo os terminais bloqueados em vez de liberar uma atualização que ainda não foi reiniciada e verificada.

As variáveis operacionais são:

```text
REGISTROFACIL_UPDATE_WORKER_COMMAND
REGISTROFACIL_RESTART_COMMAND
REGISTROFACIL_HEALTH_URL
REGISTROFACIL_UPDATE_ROOT
```

O health check padrão é `/api/system/update/health`. Em produção, o supervisor deve iniciar o novo processo, aguardar HTTP 200, confirmar a versão retornada e somente então marcar o estado como `ready`, permitindo a recarga dos terminais.

## Motor de notificações

As notificações HTTP e os toasts usam o contrato `{ success, type, title, message }`. Os tipos válidos são `success`, `danger`, `warning` e `info`; o título padrão é, respectivamente, **Sucesso**, **Erro**, **Atenção** e **Informação**. Uma resposta sem tipo não deve exibir apenas o identificador técnico do tipo: o frontend aplica o fallback contextual correspondente.

O helper JavaScript aceita o contrato novo e também normaliza as assinaturas legadas `showToast(type, message)` e `showToast(message, type)`. Isso evita quebra durante a migração gradual dos templates. Mensagens recebidas da API são escapadas antes de serem inseridas no dropdown ou no toast.

A convenção para ações é a seguinte: operações concluídas usam `success` e descrevem o resultado; dados incompletos ou ação não executada usam `warning`; falhas de servidor, permissão ou comunicação usam `danger`; carregamentos e estados informativos usam `info`. Exclusões devem ser confirmadas antes do envio e, após a resposta, devem exibir o resultado recebido — sucesso, bloqueio por vínculos ou erro — em vez de uma mensagem genérica.


## Política de anexos e imagens

A versão 3.19.0 aceita anexos de processos somente nos formatos **PDF, JPG/JPEG e PNG**, com limite máximo de 50 MB por arquivo. A extensão informada pelo usuário não é considerada suficiente: o arquivo é salvo inicialmente com nome temporário, inspecionado por `python-magic` e somente é promovido ao nome final quando o MIME real corresponde à extensão permitida.

| Fluxo | Formatos permitidos | Limite | Validação adicional |
| --- | --- | --- | --- |
| Anexos de processos | PDF, JPG/JPEG e PNG | 50 MB por arquivo | MIME real compatível com a extensão |
| Foto de perfil e usuário | JPG/JPEG e PNG | 2 MB por arquivo | MIME real compatível com a extensão |
| Logo da empresa | JPG/JPEG e PNG | Conforme o fluxo existente | MIME real compatível com a extensão |

Arquivos com extensão antiga, como DOC, DOCX, XLS, XLSX, CSV, TXT ou GIF, são rejeitados. A mesma regra vale para arquivos que tentem mascarar outro conteúdo, por exemplo, um PDF renomeado para `.jpg`. Se a validação, a gravação ou o registro no banco falhar, tanto o arquivo temporário quanto qualquer arquivo final criado durante a tentativa são removidos.

A manutenção e a exclusão continuam sendo controladas pelo vínculo do anexo com o processo. O nome físico é sempre sanitizado antes de ser usado no sistema de arquivos, e a remoção física ocorre depois da exclusão validada no banco. Antes de atualizar uma instalação existente, recomenda-se preservar a pasta de uploads; anexos legados em formatos anteriormente aceitos permanecem disponíveis para consulta, mas não podem ser enviados novamente nem substituídos por novos arquivos fora da política atual.

A cobertura automatizada está em `tests/test_file_upload_restrictions.py` e verifica a lista central de extensões, rejeição por extensão, rejeição por MIME incompatível, limpeza após falha de banco e restrição dos uploads de imagem.

## Testes específicos de anexos

Para executar somente os testes da política de arquivos:

```bash
python -m pytest tests/test_file_upload_restrictions.py -q
```

A suíte completa deve ser executada antes da publicação:

```bash
python -m pytest -q
```

A biblioteca `python-magic` é requisito de segurança para esses fluxos. Se ela não estiver disponível ou não conseguir identificar o conteúdo real, o upload deve ser bloqueado, nunca aceito por fallback baseado apenas na extensão.


## Executor externo de backup

A partir desta etapa, o backup agendado pode ser executado sem depender do processo Flask pelo comando:

```bash
python -m utils.backup_runner --source scheduled
```

O executor lê a configuração persistida, utiliza o mesmo serviço do backup manual, cria o snapshot do SQLite, valida o ZIP, calcula o SHA-256, aplica retenção e grava o status em `.backup-status.json`. Um lock exclusivo em `.backup-run.lock` impede duas execuções simultâneas para o mesmo destino.

Durante a migração, o scheduler interno continua habilitado por compatibilidade. Para transferir a responsabilidade ao sistema operacional, defina:

```text
REGISTROFACIL_INTERNAL_BACKUP_SCHEDULER=false
```

Depois, configure o agendador externo. No Windows, utilize o Agendador de Tarefas com a ação equivalente a `python -m utils.backup_runner --source scheduled`, iniciada no diretório raiz do Registro Fácil. No Linux, um exemplo de `cron` diário às 02:00 é:

```cron
0 2 * * * cd /caminho/registrofacil-v3 && /usr/bin/python3 -m utils.backup_runner --source scheduled >> /var/log/registrofacil-backup.log 2>&1
```

O processo externo é preferível para instalações importantes porque continua independente de reinícios da interface web. A aplicação ainda mantém o botão de backup manual, a listagem, o hash e o status da última execução.

A retenção padrão mantém os 14 backups válidos mais recentes. Esse valor pode ser alterado sem editar o código:

```text
REGISTROFACIL_BACKUP_RETENTION_COUNT=30
```

Arquivos inválidos não são removidos automaticamente pela retenção; eles devem ser analisados antes de qualquer limpeza manual. Isso evita que uma política de retenção destrua um artefato que precisa ser investigado.


## Preparação segura de restauração

O serviço agora oferece `stage_backup_restore()`, que valida o manifesto e o checksum lógico do ZIP, rejeita traversal de diretórios e links simbólicos, extrai o conteúdo para uma pasta temporária e executa `PRAGMA integrity_check` no banco extraído. A instalação ativa não é substituída durante essa preparação.

Essa separação é intencional. A aplicação não deve substituir o banco e os uploads ativos enquanto ainda atende requisições. A etapa de promoção deve ser executada em modo de manutenção, depois de um backup do estado atual e de uma verificação de saúde. O diretório de staging pode ser inspecionado ou usado por um operador externo para concluir a restauração de forma controlada.


## Restauração controlada de backup

A tela administrativa de backups agora oferece uma ação de restauração disponível somente para administradores e suporte. O fluxo não substitui arquivos imediatamente: primeiro valida o nome e o conteúdo do ZIP, cria um **pré-backup** do estado atual, extrai o backup em staging e executa `integrity_check` no banco extraído.

Depois dessas pré-condições, o sistema cria o marcador persistente `.restore_maintenance` fora do banco. Esse marcador faz o middleware bloquear novas operações enquanto o SQLite é substituído, inclusive se o banco antigo for trocado durante o processo. As chaves `.secret_key` e `.encryption_key` não são substituídas; a restauração preserva as chaves da instalação ativa.

A promoção cria também um rollback em `restore_rollbacks`. Banco e diretórios de uploads são substituídos por cópias temporárias e a troca do banco usa promoção atômica. Depois da troca, o sistema recria o esquema/FTS quando necessário e executa o health check. Se o health check falhar, a rotina tenta reverter automaticamente banco e uploads usando o rollback criado antes de liberar o sistema.

O rollback deve ser mantido até que o administrador confirme que a instalação restaurada está operacional. A exclusão dos rollbacks antigos deve ser uma tarefa de manutenção separada, com retenção própria; eles não devem ser apagados pela retenção normal dos ZIPs.


## Retenção de rollbacks e backup remoto

Os rollbacks de restauração agora são mantidos em `restore_rollbacks`. A rotina preserva os três diretórios mais recentes cujo nome começa por `registrofacil_rollback_` e não remove diretórios com nomes desconhecidos. O rollback criado pela restauração atual permanece disponível para inspeção e recuperação.

O formulário administrativo de backup permite selecionar `Somente local` ou `SFTP`. Quando SFTP é selecionado, host, usuário, porta, senha e caminho remoto são validados. A senha continua sendo criptografada pela camada de configuração; quando o campo de senha fica vazio em uma edição, a credencial existente é preservada.

O envio remoto não é tratado como sucesso apenas porque o `put` terminou. O scheduler verifica o tamanho do arquivo remoto e grava o estado correspondente:

| Estado | Significado |
|---|---|
| `success_local` | ZIP local validado; nenhum destino remoto configurado. |
| `success_remote` | ZIP local validado e cópia SFTP confirmada pelo tamanho. |
| `partial` | ZIP local validado, mas o envio ou a confirmação SFTP falhou. |
| `failed` | A criação ou validação do ZIP local falhou. |

O status parcial mantém o backup local disponível, mas deixa claro que a redundância remota não foi concluída. A interface administrativa exibe esse estado e o erro associado no painel da última execução.


## Teste preventivo de SFTP

A aba de backup das configurações possui o botão **Testar SFTP**. O teste usa os valores preenchidos no formulário; se a senha estiver vazia, utiliza a credencial já armazenada. Ele valida host, porta, usuário, senha, caminho absoluto e existência de um diretório remoto acessível.

O teste não salva as alterações nem cria diretórios remotos. Para ativar o destino, o administrador deve executar o teste com sucesso e depois salvar a configuração. O scheduler só considera o envio remoto concluído depois de confirmar o tamanho do arquivo enviado.


## Migração opcional de avaliações no SQLite

A migração 007 trata o pacote opcional de avaliações de forma compatível com SQLite. Ela primeiro verifica se a tabela `reviews` existe; quando o recurso não está instalado, a migração é ignorada sem falha. Quando a tabela existe, cada coluna é adicionada separadamente após consulta a `PRAGMA table_info(reviews)`, e o índice `reviews_service_id_idx` é criado com `CREATE INDEX IF NOT EXISTS`.

A migração não usa `ADD COLUMN IF NOT EXISTS` nem a referência PostgreSQL `services(id)`, pois essas construções não correspondem ao banco atual do Registro Fácil. A instalação continua compatível com bancos legados e a migração é idempotente.


## Identidade visual e preferências por usuário

O sistema dispõe de **30 temas institucionais completos**, definidos em `data/themes.py` e gerados para `static/css/color-themes.css`. Cada tema possui exatamente cinco cores de identidade: primária/sidebar, hover, acento, fundo e superfície. O **Preto Fosco Administrativo** (`paleta-01`) é o tema padrão para usuários sem preferência registrada. Entre as opções obrigatórias estão o tema neutro administrativo, o **Azul Marinho Registral** e o **Vinho Cartorial**; o catálogo também inclui famílias quentes controladas de ouro, âmbar, laranja, coral, rubi, granada, terracota, mostarda, bronze e pêssego terroso. Todas as famílias foram escolhidas para manter baixa saturação, conforto visual e diferenciação cromática.

A escolha do tema é persistida por usuário na tabela `user_preferences.tema_cor` e controla superfícies, sidebar, tipografia, bordas, botões, formulários, tabelas, modais, alertas, autenticação e telas públicas. Não existe preferência separada para a sidebar: cada tema define integralmente o corpo da sidebar, hover, item ativo e contraste da navegação.

O catálogo expõe as cinco cores diretamente no seletor de aparência em `templates/perfil.html`, enquanto os tokens derivados continuam fornecendo variações de hover, estados de sucesso/erro/aviso e acessibilidade. O CSS deve ser regenerado com `python tools/gerar_themes_css.py`; a sincronização é verificada por `python tools/verificar_themes.py`.
