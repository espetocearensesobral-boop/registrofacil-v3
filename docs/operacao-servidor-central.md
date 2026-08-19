# Operação do Registro Fácil em servidor central

**Versão:** 3.28.44
**Modelo:** Opção A — aplicação central iniciada no logon  
**Terminais previstos:** 10 usuários, com possibilidade de crescimento controlado

## Arquitetura

Uma única máquina central executa `RegistroFacil.exe`, mantém o SQLite e serve a aplicação web pelo Waitress na porta TCP 5000. Os terminais não recebem cópia do banco e não devem abrir o arquivo SQLite por compartilhamento de pasta. Cada usuário acessa o endereço da máquina central pelo navegador.

> Exemplo: `http://192.168.0.10:5000`

A máquina central precisa permanecer ligada durante o horário de operação e deve receber IP reservado no roteador ou utilizar um nome DNS/NetBIOS estável. O instalador cria uma Tarefa Agendada no logon, com `--no-browser`, para evitar que a máquina central abra uma janela de navegador automaticamente.

## Instalação no servidor

| Etapa | Procedimento |
|---|---|
| Build | Executar `BUILD_WINDOWS.bat` em uma máquina Windows com Python 3.11. O script cria `.venv-build`, instala runtime e dependências de build e gera `dist\RegistroFacil`. |
| Instalador | Compilar `INSTALADOR_RegistroFacil.iss` com Inno Setup 6. O fallback atual é 3.28.44; o parâmetro `/DMyAppVersion=...` pode ser usado para uma release posterior. |
| Rede | Permitir TCP 5000 somente no perfil Private e na sub-rede local. Não publicar a porta diretamente na internet. |
| Dados | O banco, chaves, logs, uploads e backups ficam em `C:\ProgramData\RegistroFacil`. |
| Primeiro acesso | Abrir `http://IP-DO-SERVIDOR:5000`, entrar com o usuário administrativo e concluir a troca de senha quando solicitada. |

## Configuração dos terminais

Nos terminais, não é necessário instalar o Registro Fácil nem copiar o banco. Basta abrir o navegador e acessar a URL central. O script `CRIAR_ATALHO_TERMINAL.bat` cria um atalho `.url` na Área de Trabalho:

```bat
CRIAR_ATALHO_TERMINAL.bat http://192.168.0.10:5000
```

Se o IP do servidor mudar, os atalhos precisam ser atualizados ou substituídos por um nome fixo da máquina.

## Presença dos usuários

A tela **Cópia de Segurança** possui o botão **Usuários na rede**, disponível para administradores e suporte. O modal apresenta usuários cadastrados, contadores de cadastrados/online/offline, nome, usuário, IP observado, última atividade e estado atual.

O status online não significa que existe uma conexão TCP permanente. Ele é calculado por heartbeat e última atividade: após 120 segundos sem atividade registrada, o usuário passa para offline. O logout limpa imediatamente o estado online, mas preserva o último IP observado para diagnóstico administrativo.

O endpoint de presença não retorna senha, token, epoch de sessão, e-mail ou outras credenciais. A consulta é protegida por sessão administrativa.

## Backup e atualização

O scheduler interno permanece habilitado porque a arquitetura central deve possuir apenas uma instância do aplicativo. Isso evita duplicidade de backup entre processos. O executor externo `utils/backup_runner.py` continua disponível para uma futura tarefa independente, caso a operação passe a exigir backup fora do ciclo do servidor web.

O health-check operacional é:

```text
http://127.0.0.1:5000/api/system/update/health
```

Ele retorna o estado `ok` e a versão atual. No executável frozen, o worker de atualização é iniciado pelo próprio binário com `RegistroFacil.exe --update-worker`. A troca automática de release via ponteiro `current.json` ainda exige um supervisor/relauncher específico antes de ser considerada uma atualização totalmente autônoma.

## Crescimento de usuários

A quantidade de usuários cadastrados não é o limite principal. O que deve ser acompanhado é a concorrência de leitura/escrita, a latência e os erros de lock. Para o cenário atual de 10 usuários, com margem inicial para uso moderado de aproximadamente 20–30 usuários, a instalação central com SQLite é adequada desde que exista somente uma instância do servidor.

Se houver muitas gravações simultâneas, várias unidades, acesso remoto ou crescimento acima desse perfil, deve ser planejada a migração para PostgreSQL ou MariaDB/MySQL. O acesso dos terminais continuará sendo pelo navegador; somente o banco e a configuração interna mudariam.

## Diagnóstico rápido

| Sintoma | Verificação |
|---|---|
| Terminal não abre a tela | Testar `ping IP-DO-SERVIDOR`, confirmar perfil Private e testar TCP 5000. |
| Aplicação abre no servidor, mas não nos terminais | Conferir se o servidor está em `0.0.0.0:5000` e se a regra do firewall aponta para `localsubnet`. |
| Dois processos aparecem | Encerrar o processo duplicado; a checagem preventiva da porta e a tarefa `MultipleInstances IgnoreNew` devem evitar novas duplicações. |
| Usuário aparece offline | Verificar se a página está aberta/visível e aguardar o próximo heartbeat de até 60 segundos. |
| Backup não executa | Conferir a configuração em Cópia de Segurança, os logs e o diretório `C:\ProgramData\RegistroFacil\backups`. |
| Atualização fica em `ready_to_restart` | O health-check está corrigido, mas a ativação automática da release ainda depende de um supervisor/relauncher de produção. |
