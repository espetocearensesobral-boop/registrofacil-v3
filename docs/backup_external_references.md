# Referências externas para backup e restauração

[1] SQLite Backup API: https://sqlite.org/backup.html

A Online Backup API copia uma base SQLite em execução para um arquivo de destino e produz um snapshot consistente sem exigir bloqueio prolongado durante toda a operação. A documentação também alerta para tratar erros de lock e busy/locked.

[2] SQLite Write-Ahead Logging: https://www.sqlite.org/wal.html

O modo WAL usa arquivos auxiliares `-wal` e `-shm`, exige atenção a checkpoint e requer que os processos estejam no mesmo host. Estratégias baseadas em cópia direta precisam considerar esses arquivos; a Online Backup API é preferível para snapshot do banco ativo.

[3] APScheduler User Guide: https://apscheduler.readthedocs.io/en/master/userguide.html

O scheduler executa tarefas em background, possui controle de concorrência por tarefa e opções de coalescência e tolerância para execuções perdidas. A coordenação entre múltiplas instâncias depende de armazenamento/event broker apropriados; um scheduler local em memória não deve ser tratado como coordenador distribuído.
