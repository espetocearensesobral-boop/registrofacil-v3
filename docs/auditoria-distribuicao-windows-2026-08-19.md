# Auditoria da distribuição Windows — Registro Fácil

**Data:** 19/08/2026  
**Versão analisada:** 3.28.42  
**Repositório:** [espetocearensesobral-boop/registrofacil-v3](https://github.com/espetocearensesobral-boop/registrofacil-v3)

## 1. Escopo e conclusão executiva

Foi revisada a cadeia de compilação, empacotamento PyInstaller, dependências, instalador Inno Setup, criação de atalhos, inicialização automática, execução como processo persistente, scheduler interno, executor externo de backup e integração do atualizador.

A aplicação possui uma base funcional importante: usa Waitress em vez do servidor de desenvolvimento, separa dados mutáveis do bundle quando executada como `.exe`, mantém chaves persistentes, possui backup externo com lock exclusivo, validação SHA-256 de releases e testes automatizados para os fluxos de atualização e backup.

Entretanto, a distribuição Windows ainda não está coerente com a versão atual nem com a arquitetura de atualização existente. Os dois artefatos de release estão defasados: `BUILD_WINDOWS.bat` declara **3.27.0**, enquanto `INSTALADOR_RegistroFacil.iss` declara **3.17.6** e o código está em **3.28.42**. Além disso, o instalador cria uma Tarefa Agendada para iniciar o aplicativo no logon, mas não instala nem configura um serviço Windows real. O executável também tenta abrir o navegador sempre que é iniciado, comportamento inadequado para um serviço ou supervisor.

> **Conclusão:** antes de publicar uma nova distribuição Windows, é necessário escolher formalmente entre um modelo de aplicativo local iniciado no logon e um modelo de servidor Windows persistente com serviço. A implementação atual mistura os dois modelos.

## 2. Fluxo atual identificado

| Camada | Implementação atual | Situação |
|---|---|---|
| Desenvolvimento | `python app.py` | Funciona como servidor local e abre o navegador. |
| Servidor HTTP | Waitress em `0.0.0.0:5000`, oito threads | Funcional, porém mais amplo do que o necessário para uma aplicação local. |
| Empacotamento | PyInstaller `--onedir --windowed` | Funcional em princípio, mas excessivamente dependente de parâmetros manuais e hidden imports. |
| Dados frozen | `C:\ProgramData\RegistroFacil` | Coerente com instalação em `Program Files`, porém a ACL atual é ampla. |
| Inicialização | Tarefa Agendada `AtLogOn` | Não é serviço Windows; depende de usuário logado. |
| Navegador | Thread automática em `app.py` | Adequada para atalho interativo, inadequada para serviço. |
| Backup interno | APScheduler dentro do Flask | Pode duplicar se o executável for iniciado mais de uma vez. |
| Backup externo | `python -m utils.backup_runner --source scheduled` | Implementado e com lock; ainda não integrado ao instalador. |
| Atualização | Worker externo e `current.json` | Arquitetura segura, mas sem restart/health-check configurados pela instalação. |

## 3. Achados críticos

### 3.1 Versões divergentes nos artefatos de release

O código fonte está em 3.28.42, mas o script de compilação ainda anuncia 3.27.0 e o instalador ainda anuncia 3.17.6. Isso afeta o nome do executável final, o nome do instalador, o registro de desinstalação, os textos exibidos ao usuário e a identificação de releases. A origem atual está em [`config.py`](https://github.com/espetocearensesobral-boop/registrofacil-v3/blob/main/config.py), [`BUILD_WINDOWS.bat`](https://github.com/espetocearensesobral-boop/registrofacil-v3/blob/main/BUILD_WINDOWS.bat) e [`INSTALADOR_RegistroFacil.iss`](https://github.com/espetocearensesobral-boop/registrofacil-v3/blob/main/INSTALADOR_RegistroFacil.iss).

**Prioridade:** P0. Deve existir uma única versão de release, gerada no início da compilação e reutilizada no PyInstaller, no Inno Setup, no manifesto e no arquivo `versao.txt`.

### 3.2 A variável `WEASYPRINT_EXCLUDE` não é aplicada

O BAT detecta a ausência do WeasyPrint e monta a variável `WEASYPRINT_EXCLUDE`, mas essa variável não é expandida no comando PyInstaller. Na prática, o script informa que continuará sem WeasyPrint, mas ainda executa o comando sem os parâmetros de exclusão. Como as rotas importam WeasyPrint no carregamento, a compilação pode falhar ou gerar um executável que falha ao iniciar.

**Prioridade:** P0. O build deve ter dois perfis explícitos: **com PDF**, exigindo dependências nativas verificadas; ou **sem PDF**, compilando uma variante com dependências e rotas opcionais claramente tratadas. O comportamento silencioso atual não é confiável.

### 3.3 O build não é reprodutível

O `BUILD_WINDOWS.bat` atualiza o `pip`, instala dependências diretamente no Python global e instala o PyInstaller fora do `requirements.txt`. Isso pode alterar o ambiente do computador de build e produzir executáveis diferentes em compilações sucessivas. Também não há uma versão de Python/arquitetura formalmente fixada, nem um arquivo de dependências exclusivo de build.

**Prioridade:** P1. Criar um ambiente virtual descartável, instalar `requirements.txt` e `requirements-build.txt` com versões fixadas, registrar `python --version`, `pip freeze`, arquitetura e hash do artefato. O build deve falhar imediatamente quando a instalação de uma dependência falhar; atualmente há um aviso e a execução continua após falhas no `requirements.txt`.

### 3.4 O instalador está defasado e mistura modelos de execução

O Inno Setup instala o bundle em `Program Files`, cria diretórios mutáveis em `ProgramData`, cria atalhos e oferece autostart. Essa separação é conceitualmente correta. Porém, a tarefa de autostart inicia o executável completo no logon, e o executável completo também abre o navegador. Isso caracteriza um aplicativo interativo, não um serviço.

O instalador não instala um supervisor, não registra um serviço Windows, não configura `REGISTROFACIL_RESTART_COMMAND`, não configura `REGISTROFACIL_HEALTH_URL` e não configura o comando do worker de atualização. Consequentemente, o worker pode preparar a atualização e parar em `ready_to_restart`, sem conseguir reiniciar e validar a nova release.

**Prioridade:** P0 para o fluxo de atualização e P1 para a escolha do modelo de execução.

### 3.5 Health-check inconsistente no worker

O endpoint real exposto pelo blueprint é `/api/system/update/health`, conforme [`routes/system_updates.py`](https://github.com/espetocearensesobral-boop/registrofacil-v3/blob/main/routes/system_updates.py). O worker usa por padrão `http://127.0.0.1:5000/api/system/health`, que não corresponde ao endpoint existente. A documentação também registra `/api/system/update/health` como o endpoint correto.

Sem uma variável de ambiente corrigindo manualmente o endereço, o restart pode subir o processo e ainda assim declarar falha porque o health-check consulta uma rota inexistente.

**Prioridade:** P0. O default do worker deve ser alinhado ao endpoint real e o health-check deve validar também a versão retornada, não apenas HTTP 200.

### 3.6 `current.json` exige um supervisor real

O launcher de atualização prepara releases em `ProgramData\RegistroFacil\updates`, grava `current.json` atomically e preserva o banco, uploads e chaves. Entretanto, o aplicativo empacotado continua sendo iniciado pelo caminho fixo `{app}\RegistroFacil.exe`. O ponteiro, sozinho, não troca o executável em execução.

Isso não é um defeito do launcher; é uma dependência arquitetural. É necessário um supervisor que leia o ponteiro, encerre o processo antigo, inicie a release indicada, aguarde o health-check, confirme a versão e faça rollback em caso de falha.

**Prioridade:** P0 para considerar o atualizador pronto para produção.

### 3.7 Permissões de dados amplas

O instalador aplica `Permissions: users-full` em `C:\ProgramData\RegistroFacil` e subpastas. Isso permite que qualquer usuário local modifique banco, uploads, logs e potencialmente arquivos sensíveis, incluindo chaves persistentes como `.secret_key` e `.encryption_key`. Em uma máquina compartilhada, essa ACL é ampla demais.

**Prioridade:** P0/P1, conforme o modelo escolhido. Para instalação por máquina com serviço, o ideal é conceder acesso somente ao serviço/usuário operacional, além de `SYSTEM` e `Administrators`. Para instalação por usuário, é mais seguro usar `%LOCALAPPDATA%\RegistroFacil` e evitar um diretório compartilhado.

## 4. Atalhos e inicialização

O instalador cria um atalho no grupo do Menu Iniciar, um atalho opcional na Área de Trabalho e uma segunda entrada em `{userprograms}`. Essa última normalmente também corresponde a uma localização do Menu Iniciar, podendo produzir uma duplicação. O texto comenta “Taskbar/Quick Launch”, mas a entrada não fixa o aplicativo na barra de tarefas e não equivale a um atalho moderno de Quick Launch.

A tarefa `autostart` é criada com gatilho `AtLogOn`, execução elevada e `MultipleInstances IgnoreNew`. Ela depende de uma sessão de usuário e não garante que o aplicativo seja executado quando nenhum usuário estiver conectado. Para uma aplicação local com interface no navegador, essa limitação é aceitável e deve ser documentada. Para disponibilidade contínua, é insuficiente.

A regra de firewall atual libera entrada para qualquer perfil (`profile=any`) e para o executável. Como a aplicação é local e o navegador acessa `localhost`, a recomendação é remover a regra e fazer o servidor escutar em `127.0.0.1`. Se houver necessidade real de acesso de outra máquina, a regra deve ser criada com escopo restrito, porta definida, perfil de rede apropriado e justificativa operacional.

## 5. Backup e execução duplicada

O projeto já possui o executor externo [`utils/backup_runner.py`](https://github.com/espetocearensesobral-boop/registrofacil-v3/blob/main/utils/backup_runner.py), que não inicia Flask nem APScheduler e possui lock exclusivo. Ele é a melhor base para o Agendador de Tarefas do Windows.

O scheduler interno continua habilitado por padrão. Se o executável for iniciado por atalho, autostart e um eventual serviço, cada processo pode inicializar seu próprio scheduler e tentar executar o backup. O desenho recomendado é escolher uma única autoridade: ou APScheduler interno, ou Agendador de Tarefas externo com `REGISTROFACIL_INTERNAL_BACKUP_SCHEDULER=false`. Para instalações Windows mais importantes, o executor externo é preferível porque não depende da interface web estar aberta.

## 6. Arquivos de dependência

O `requirements.txt` possui boas versões fixadas para o runtime, incluindo Flask, Waitress, APScheduler, SQLite/criptografia, WeasyPrint, OpenPyXL, Paramiko, Flask-Mail e `python-magic` com variante condicional para Windows. Ainda assim, o PyInstaller não está declarado como dependência de build, e não existe uma separação formal entre runtime e ferramentas de compilação.

A recomendação é manter:

| Arquivo | Conteúdo recomendado |
|---|---|
| `requirements.txt` | Somente runtime necessário para execução do aplicativo. |
| `requirements-build.txt` | PyInstaller, ferramentas de validação, gerador de manifesto e dependências de empacotamento. |
| `requirements-dev.txt` | Pytest, linters, ferramentas de desenvolvimento e análise. |
| `runtime.version` ou equivalente | Versão mínima de Python e arquitetura suportada. |

A dependência de WeasyPrint deve ser testada como requisito de PDF, pois a presença do pacote Python não garante que todos os componentes nativos estejam disponíveis no Windows.

## 7. Arquitetura recomendada

### Opção A — Aplicativo local iniciado no logon

Esta é a opção mais simples e mais alinhada ao comportamento atual. O instalador mantém um aplicativo de usuário iniciado pelo Agendador de Tarefas no logon, desativa a abertura do navegador quando executado em modo de manutenção, remove a regra ampla de firewall, mantém o serviço HTTP em `127.0.0.1` e configura o backup externo em uma tarefa separada.

O usuário abriria o sistema pelo Menu Iniciar ou Área de Trabalho. O backup rodaria independentemente pelo Agendador de Tarefas. A atualização seria concluída por um pequeno supervisor/relauncher ou por um instalador de atualização que pare o processo, ative a release, reinicie e confirme a versão.

### Opção B — Serviço Windows real

Esta opção é recomendada quando o sistema precisa permanecer disponível sem usuário conectado. Nesse modelo, o servidor deve ser iniciado sem navegador, rodar com uma conta operacional dedicada, ter recuperação automática após falha, health-check, logs e parada controlada. A interface seria aberta separadamente por um atalho.

A implementação exige um supervisor real, como um wrapper Windows Service ou serviço nativo via `pywin32`, além de ajustes no Inno Setup. Também exige definir ACLs adequadas para `ProgramData`, porque o serviço não deve compartilhar chaves e banco com usuários locais sem controle.

> **Recomendação:** começar pela Opção A, porque ela exige menos mudanças e corresponde ao uso atual da aplicação. Migrar para a Opção B somente se houver necessidade de execução sem usuário logado ou de alta disponibilidade local.

## 8. Plano de melhorias priorizado

| Prioridade | Melhoria | Resultado esperado |
|---|---|---|
| P0 | Sincronizar versão 3.28.42 no BAT, ISS, manifesto e artefatos | Evita releases identificadas incorretamente. |
| P0 | Corrigir o default do health-check para `/api/system/update/health` | Permite concluir reinício e atualização. |
| P0 | Separar modo interativo de modo serviço e controlar abertura do navegador por ambiente | Evita janelas inesperadas em supervisor/serviço. |
| P0 | Definir ACL segura para dados, chaves, banco e uploads | Reduz risco de adulteração local. |
| P1 | Criar `requirements-build.txt` e build reprodutível em ambiente virtual | Reduz diferenças entre máquinas de compilação. |
| P1 | Corrigir a aplicação efetiva de `WEASYPRINT_EXCLUDE` ou tornar PDF requisito obrigatório | Evita falso sucesso na compilação. |
| P1 | Criar smoke test do `.exe`: iniciar, consultar health, confirmar versão e encerrar | Detecta bundle quebrado antes do instalador. |
| P1 | Integrar o `backup_runner` a uma tarefa externa e desativar o scheduler interno | Evita backups duplicados. |
| P1 | Remover duplicação de atalhos e retirar a regra de firewall ampla | Instalação mais limpa e menor superfície de rede. |
| P2 | Criar supervisor/relauncher com rollback e confirmação de versão | Completa o atualizador sem depender de ação manual. |
| P2 | Automatizar geração de ZIP, SHA-256 e `manifest.json` | Reduz erros na publicação. |
| P2 | Adicionar logs de instalação, inicialização e atualização com caminho visível | Facilita suporte e diagnóstico em máquinas de clientes. |

## 9. Checklist recomendado antes de uma nova distribuição

1. Confirmar uma única versão de release em `config.py`, BAT, ISS, manifesto e nome do artefato.
2. Compilar em ambiente virtual limpo e registrar a versão do Python, arquitetura e `pip freeze`.
3. Executar o build com e sem o perfil de PDF, conforme a política escolhida.
4. Validar a existência de templates, estáticos, ícone, rotas, módulos `data`, `routes` e `utils` no bundle.
5. Iniciar o executável em modo interativo e consultar o endpoint de health.
6. Iniciar o executável em modo não interativo e confirmar que nenhum navegador é aberto.
7. Testar o primeiro acesso, criação do banco, geração das chaves, migrações e gravação em `ProgramData` ou `LocalAppData`.
8. Instalar uma versão anterior, atualizar para a nova e confirmar preservação do banco, uploads e chaves.
9. Testar desinstalação mantendo os dados, conforme a política definida, e remover tarefas/serviços sem deixar processos ativos.
10. Executar backup externo, confirmar lock, ZIP, SHA-256, retenção e status.
11. Simular falha de restart e confirmar que a atualização não marca a versão como pronta sem health-check válido.
12. Testar usuário sem privilégio administrativo e uma máquina com mais de um usuário local.

## 10. Escopo desta revisão

Nesta etapa foi realizada a auditoria e não foram alterados os scripts de build, o instalador, as dependências ou o modelo de serviço, porque essas mudanças afetam diretamente a instalação existente e dependem da escolha entre aplicativo no logon e serviço Windows real. O próximo passo seguro é aplicar a Opção A, salvo se houver necessidade explícita de execução sem usuário conectado.

## Referências

[1]: https://github.com/espetocearensesobral-boop/registrofacil-v3/blob/main/BUILD_WINDOWS.bat "Script atual de compilação Windows"

[2]: https://github.com/espetocearensesobral-boop/registrofacil-v3/blob/main/INSTALADOR_RegistroFacil.iss "Script atual do instalador Inno Setup"

[3]: https://github.com/espetocearensesobral-boop/registrofacil-v3/blob/main/app.py "Inicialização da aplicação e servidor Waitress"

[4]: https://github.com/espetocearensesobral-boop/registrofacil-v3/blob/main/config.py "Configuração de dados e execução frozen"

[5]: https://github.com/espetocearensesobral-boop/registrofacil-v3/blob/main/data/update_worker.py "Worker externo de atualização"

[6]: https://github.com/espetocearensesobral-boop/registrofacil-v3/blob/main/routes/system_updates.py "Endpoints de atualização e health-check"

[7]: https://github.com/espetocearensesobral-boop/registrofacil-v3/blob/main/utils/backup_runner.py "Executor externo de backup"

## 8. Estado pós-implementação — versão 3.28.43

As recomendações prioritárias foram aplicadas para o modelo de instalação central iniciado no logon. O build agora usa ambiente virtual próprio, instala `requirements-build.txt`, exige WeasyPrint para manter PDF funcional, sincroniza a versão do código e gera `versao.txt`. O Inno Setup passou a usar a mesma versão, eliminou o atalho duplicado, restringiu a regra de firewall à porta TCP 5000 na sub-rede local e inicia a Tarefa Agendada com `--no-browser --host 0.0.0.0 --port 5000`.

O executável passou a aceitar modos explícitos de servidor central, worker de atualização e executor de backup. Também foi adicionada uma verificação preventiva da porta para evitar que uma segunda instância inicialize o scheduler antes de falhar na porta. O worker frozen agora é acionado como `RegistroFacil.exe --update-worker`, e o health-check padrão foi alinhado ao endpoint `/api/system/update/health`, que retorna a versão atual.

A arquitetura continua sendo a Opção A: uma única máquina central executa o Registro Fácil e os terminais acessam por navegador via IP ou nome da máquina. O SQLite permanece local ao processo do servidor; o arquivo não deve ser compartilhado diretamente pela rede. O scheduler interno de backup foi preservado porque existe apenas uma instância central, evitando alteração funcional do fluxo de backup configurado pela aplicação.

Também foi implementado o monitoramento administrativo de presença em Cópia de Segurança. A tabela `user_presence` guarda somente o último heartbeat e o último IP observado. O estado online expira após 120 segundos sem atividade, o logout limpa o estado online e o endpoint é restrito a administradores/suporte. O modal mostra contadores, nome, usuário, IP, última atividade e estado online/offline, com atualização automática a cada 30 segundos.

As validações executadas após a implementação foram: contrato Windows aprovado, lint de UI aprovado, temas sincronizados, compilação Python aprovada, diff sem erros e suíte completa com 80 testes aprovados.
