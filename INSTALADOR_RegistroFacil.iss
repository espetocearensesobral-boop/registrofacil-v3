; ============================================================================
;  RegistroFacil - Script de Instalador Profissional
;  Gerado para Inno Setup 6.x (download: https://jrsoftware.org/isinfo.php)
;
;  Recursos:
;    - Compativel com x64 e x32 (Windows 10/11)
;    - Atalhos no Desktop e Menu Iniciar
;    - Inicializacao automatica com o Windows (opcional)
;    - Desinstalador completo e automatico
;    - Pagina de licenca, boas-vindas e conclusao personalizada
;    - Pagina de tarefas extras (autostart, atalho desktop)
;    - Deteccao de versao anterior com atualizacao silenciosa
;    - Verificacao de permissao de administrador
; ============================================================================

#define MyAppName        "Registro Facil"
#ifndef MyAppVersion
#define MyAppVersion     "3.28.54"
#endif
#define MyAppPublisher   "Tauan Pires"
#define MyAppExeName     "RegistroFacil.exe"
#define MyAppId          "{A1B2C3D4-E5F6-7890-ABCD-EF1234567890}"
#define MySourceDir      "dist\RegistroFacil"
#define MyIconFile       "static\img\certificate.ico"
#define MySmallImage     "static\img\certificate.png"
#define MyLargeImage     "static\img\registrofacil.png"

[Setup]
; ── Identidade da aplicacao ────────────────────────────────────────────────
AppId                   = {{A1B2C3D4-E5F6-7890-ABCD-EF1234567890}
AppName                 = {#MyAppName}
AppVersion              = {#MyAppVersion}
AppVerName              = {#MyAppName} {#MyAppVersion}
AppPublisher            = {#MyAppPublisher}
AppPublisherURL         = https://github.com/espetocearensesobral-boop/registrofacil-v3
AppSupportURL           = https://github.com/espetocearensesobral-boop/registrofacil-v3/issues
AppUpdatesURL           = https://github.com/espetocearensesobral-boop/registrofacil-v3/releases
AppCopyright            = Copyright (C) 2025 {#MyAppPublisher}

; ── Pasta de instalacao padrao ─────────────────────────────────────────────
; Instala em "C:\Program Files\Registro Facil" (respeita x64/x32)
DefaultDirName          = {autopf}\{#MyAppName}
DefaultGroupName        = {#MyAppName}
AllowNoIcons            = yes

; ── Arquivo de saida do instalador ────────────────────────────────────────
OutputDir               = instalador_saida
OutputBaseFilename      = RegistroFacil_v{#MyAppVersion}_Setup
SetupIconFile           = {#MyIconFile}

; ── Imagens da interface ───────────────────────────────────────────────────
; WizardImageFile  : imagem lateral (164x314 px, BMP ou PNG)
; WizardSmallImage : imagem do canto superior direito (55x58 px)
WizardImageFile         = {#MyLargeImage}
WizardSmallImageFile    = {#MySmallImage}
WizardStyle             = modern
WizardSizePercent       = 100

; ── Compressao ────────────────────────────────────────────────────────────
Compression             = lzma2/ultra64
SolidCompression        = yes
LZMAUseSeparateProcess  = yes

; ── Compatibilidade x64/x32 ──────────────────────────────────────────────
; O instalador e nativamente 32-bit, mas instala no local correto (x64 ou x32)
ArchitecturesInstallIn64BitMode = x64compatible
ArchitecturesAllowed    = x64compatible x86

; ── Privilegios e protecao ────────────────────────────────────────────────
PrivilegesRequired      = admin
PrivilegesRequiredOverridesAllowed = dialog
CreateUninstallRegKey   = yes
UninstallDisplayIcon    = {app}\{#MyAppExeName}
UninstallDisplayName    = {#MyAppName} {#MyAppVersion}

; ── Configuracoes de versao para atualizacao ─────────────────────────────
VersionInfoVersion      = {#MyAppVersion}.0
VersionInfoCompany      = {#MyAppPublisher}
VersionInfoDescription  = {#MyAppName} - Sistema de Gestao de Processos
VersionInfoProductName  = {#MyAppName}
VersionInfoCopyright    = {#MyAppPublisher}

; ── Reinicio opcional ─────────────────────────────────────────────────────
RestartIfNeededByRun    = no

; ── Informacoes exibidas em "Adicionar/Remover Programas" ─────────────────
ChangesAssociations     = no
ChangesEnvironment      = no

; ── Idioma do instalador ──────────────────────────────────────────────────
; O arquivo de idioma Portuguese.isl deve estar na pasta do Inno Setup.
; Se nao estiver, o Inno Setup usara o ingles por padrao.

[Languages]
Name: "ptBR"; MessagesFile: "compiler:Languages\BrazilianPortuguese.isl"

[CustomMessages]
ptBR.CreateDesktopIcon=Criar atalho na &Área de Trabalho
ptBR.CreateQuickLaunchIcon=Criar atalho na Barra de &Ferramentas de Acesso Rápido
ptBR.LaunchAutostart=Iniciar &automaticamente com o Windows
ptBR.LaunchAfterInstall=Abrir &Registro Fácil após a instalação
ptBR.WelcomeTitle=Bem-vindo ao Registro Fácil!
ptBR.WelcomeText=Este assistente irá instalar o Registro Fácil {#MyAppVersion} em seu computador.%n%nO Registro Fácil é um sistema completo de gestão de processos de cartório, que roda diretamente no seu navegador sem necessidade de internet.%n%nClique em Avançar para continuar ou em Cancelar para sair.
ptBR.FinishedTitle=Instalação do Registro Fácil Concluída!
ptBR.FinishedText=O Registro Fácil foi instalado com sucesso em seu computador.%n%nO sistema iniciará automaticamente e abrirá no seu navegador padrão.%n%nClique em Concluir para finalizar.

[Tasks]
; Tarefas extras exibidas durante a instalacao
Name: "desktopicon";     Description: "{cm:CreateDesktopIcon}";             GroupDescription: "Atalhos:"; Flags: unchecked
Name: "autostart";       Description: "{cm:LaunchAutostart}";               GroupDescription: "Inicialização:";
Name: "launchafterinstall"; Description: "{cm:LaunchAfterInstall}";         GroupDescription: "Após a instalação:"; Flags: unchecked

[Dirs]
; {app} = C:\Program Files\Registro Facil  → apenas leitura (exe e assets)
; Dados gravados em C:\ProgramData\RegistroFacil → acessivel sem admin
Name: "{commonappdata}\RegistroFacil";                  Permissions: users-modify
Name: "{commonappdata}\RegistroFacil\logs";             Permissions: users-modify
Name: "{commonappdata}\RegistroFacil\backups";          Permissions: users-modify
Name: "{commonappdata}\RegistroFacil\uploads";          Permissions: users-modify
Name: "{commonappdata}\RegistroFacil\uploads\processos"; Permissions: users-modify
Name: "{commonappdata}\RegistroFacil\uploads\perfil";    Permissions: users-modify
Name: "{commonappdata}\RegistroFacil\uploads\empresa";   Permissions: users-modify
Name: "{commonappdata}\RegistroFacil\temp";             Permissions: users-modify

[Files]
; ── Arquivos do executavel compilado ──────────────────────────────────────
; Copia TODOS os arquivos da pasta dist\RegistroFacil gerada pelo PyInstaller
Source: "{#MySourceDir}\*";             DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

; ── Icone da aplicacao ────────────────────────────────────────────────────
Source: "static\img\certificate.ico"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
; ── Atalho no Menu Iniciar ────────────────────────────────────────────────
Name: "{group}\{#MyAppName}";                       FileName: "{app}\{#MyAppExeName}"; IconFilename: "{app}\certificate.ico"; Comment: "Abrir o Sistema Registro Fácil"
Name: "{group}\Desinstalar {#MyAppName}";           FileName: "{uninstallexe}"; IconFilename: "{app}\certificate.ico"

; ── Atalho na Área de Trabalho (opcional - tarefa) ───────────────────────
Name: "{autodesktop}\{#MyAppName}";                 FileName: "{app}\{#MyAppExeName}"; IconFilename: "{app}\certificate.ico"; Comment: "Abrir o Sistema Registro Fácil"; Tasks: desktopicon

; ── Atalho de Inicio Rapido / Taskbar (Windows 10/11) ────────────────────

[Registry]
; ── Informacoes de desinstalacao no Painel de Controle ───────────────────
Root: HKLM; Subkey: "Software\Microsoft\Windows\CurrentVersion\Uninstall\{{A1B2C3D4-E5F6-7890-ABCD-EF1234567890}_is1"; ValueType: string; ValueName: "DisplayIcon";       ValueData: "{app}\certificate.ico"; Flags: uninsdeletekey
Root: HKLM; Subkey: "Software\Microsoft\Windows\CurrentVersion\Uninstall\{{A1B2C3D4-E5F6-7890-ABCD-EF1234567890}_is1"; ValueType: string; ValueName: "DisplayVersion";    ValueData: "{#MyAppVersion}"
Root: HKLM; Subkey: "Software\Microsoft\Windows\CurrentVersion\Uninstall\{{A1B2C3D4-E5F6-7890-ABCD-EF1234567890}_is1"; ValueType: string; ValueName: "Publisher";         ValueData: "{#MyAppPublisher}"
Root: HKLM; Subkey: "Software\Microsoft\Windows\CurrentVersion\Uninstall\{{A1B2C3D4-E5F6-7890-ABCD-EF1234567890}_is1"; ValueType: string; ValueName: "URLInfoAbout";      ValueData: "http://localhost:5000"
Root: HKLM; Subkey: "Software\Microsoft\Windows\CurrentVersion\Uninstall\{{A1B2C3D4-E5F6-7890-ABCD-EF1234567890}_is1"; ValueType: string; ValueName: "InstallDate";       ValueData: "{code:GetInstallDate}"
Root: HKLM; Subkey: "Software\Microsoft\Windows\CurrentVersion\Uninstall\{{A1B2C3D4-E5F6-7890-ABCD-EF1234567890}_is1"; ValueType: dword;  ValueName: "NoModify";           ValueData: 1
Root: HKLM; Subkey: "Software\Microsoft\Windows\CurrentVersion\Uninstall\{{A1B2C3D4-E5F6-7890-ABCD-EF1234567890}_is1"; ValueType: dword;  ValueName: "NoRepair";           ValueData: 1

; ── Chave do aplicativo para identificacao ────────────────────────────────
Root: HKLM; Subkey: "Software\{#MyAppPublisher}\{#MyAppName}"; ValueType: string; ValueName: "Version";     ValueData: "{#MyAppVersion}"; Flags: uninsdeletekey
Root: HKLM; Subkey: "Software\{#MyAppPublisher}\{#MyAppName}"; ValueType: string; ValueName: "InstallPath"; ValueData: "{app}"
Root: HKLM; Subkey: "Software\{#MyAppPublisher}\{#MyAppName}"; ValueType: string; ValueName: "DataPath";    ValueData: "{commonappdata}\RegistroFacil"

; ── Autostart via Tarefa Agendada (HKCU\Run nao funciona com apps elevados) ─
; A tarefa e criada/removida na secao [Run]/[UninstallRun]

; ── Firewall: permitir o executavel (porta 5000 local) ────────────────────
; Nota: a regra de firewall e criada/removida via [Run]/[UninstallRun]

[Run]
; ── Criar regra de firewall (apenas se instalado como admin) ─────────────
Filename: "{sys}\netsh.exe"; Parameters: "advfirewall firewall add rule name=""{#MyAppName}"" dir=in action=allow program=""{app}\{#MyAppExeName}"" protocol=TCP localport=5000 remoteip=localsubnet enable=yes profile=private"; StatusMsg: "Configurando firewall para a rede local..."; Flags: runhidden; Check: IsAdminInstallMode

; ── Tarefa Agendada criada via Code (ver CurStepChanged abaixo) ──────────
; PowerShell e usado para garantir quoting correto de caminhos com espacos.

; ── Abrir app apos instalacao (tarefa opcional) ───────────────────────────
Filename: "{app}\{#MyAppExeName}"; Description: "Abrir {#MyAppName}"; Flags: nowait postinstall skipifsilent; Tasks: launchafterinstall

[UninstallRun]
; ── Encerrar o processo antes de desinstalar ─────────────────────────────
Filename: "{sys}\taskkill.exe"; Parameters: "/F /IM {#MyAppExeName}"; Flags: runhidden; RunOnceId: "KillProcess"

; ── Remover Tarefa Agendada de autostart ─────────────────────────────────
Filename: "{sys}\schtasks.exe"; Parameters: "/Delete /F /TN ""{#MyAppName}"""; Flags: runhidden; RunOnceId: "RemoveTask"

; ── Remover regra de firewall ao desinstalar ──────────────────────────────
Filename: "{sys}\netsh.exe"; Parameters: "advfirewall firewall delete rule name=""{#MyAppName}"""; Flags: runhidden; RunOnceId: "RemoveFirewall"

[UninstallDelete]
; ── Remover arquivos gerados em runtime ──────────────────────────────────
; ATENCAO: dados e backups em C:\ProgramData\RegistroFacil sao MANTIDOS.
; O usuario pode remover manualmente se desejar limpeza completa.
Type: filesandordirs; Name: "{app}\_internal\*.pyc"

[Code]
// ── Criar Tarefa Agendada via PowerShell (quoting seguro para caminhos com espacos) ──
// Chamado apos a instalacao completa quando o usuario selecionou a tarefa "autostart"
procedure CreateStartupTask();
var
  ExePath, PSCmd: String;
  ResultCode: Integer;
begin
  ExePath := ExpandConstant('{app}\{#MyAppExeName}');
  // Monta o comando PowerShell sem problemas de quoting:
  //   $a = New-ScheduledTaskAction -Execute 'C:\...\RegistroFacil.exe'
  //   $t = New-ScheduledTaskTrigger -AtLogOn
  //   $s = New-ScheduledTaskSettingsSet -ExecutionTimeLimit 0 -StartWhenAvailable -MultipleInstances IgnoreNew
  //   Register-ScheduledTask -TaskName 'Registro Facil' -Action $a -Trigger $t -Settings $s -RunLevel Highest -Force
  PSCmd :=
    '$a = New-ScheduledTaskAction -Execute ''' + ExePath + ''' -Argument ''--no-browser --host 0.0.0.0 --port 5000''; ' +
    '$t = New-ScheduledTaskTrigger -AtLogOn; ' +
    '$s = New-ScheduledTaskSettingsSet -ExecutionTimeLimit 0 -StartWhenAvailable -MultipleInstances IgnoreNew; ' +
    'Register-ScheduledTask -TaskName ''{#MyAppName}'' -Action $a -Trigger $t -Settings $s -RunLevel Highest -Force';

  Exec(
    ExpandConstant('{sys}\WindowsPowerShell\v1.0\powershell.exe'),
    '-NonInteractive -WindowStyle Hidden -ExecutionPolicy Bypass -Command "' + PSCmd + '"',
    '', SW_HIDE, ewWaitUntilTerminated, ResultCode
  );
end;

// Executado ao final de cada passo da instalacao
procedure CurStepChanged(CurStep: TSetupStep);
begin
  // Cria a tarefa agendada apos todos os arquivos copiados, se o usuario escolheu autostart
  if (CurStep = ssPostInstall) and IsTaskSelected('autostart') then
    CreateStartupTask();
end;

// Retorna a data atual no formato YYYYMMDD para o registro
function GetInstallDate(Param: String): String;
begin
  Result := GetDateTimeString('yyyymmdd', #0, #0);
end;

// Verifica se ha uma versao anterior instalada e pergunta ao usuario
function InitializeSetup(): Boolean;
var
  OldVersion: String;
  UninstallPath: String;
  UninstallResult: Integer;
begin
  Result := True;

  // Verificar versao anterior via registro
  if RegQueryStringValue(HKLM,
    'Software\' + '{#MyAppPublisher}' + '\' + '{#MyAppName}',
    'Version', OldVersion) then
  begin
    // Ha uma versao instalada - verificar se e diferente
    if OldVersion <> '{#MyAppVersion}' then
    begin
      if MsgBox('Uma versao anterior do ' + '{#MyAppName}' + ' (' + OldVersion + ') foi encontrada.' + #13#10 +
                'Deseja atualizá-la para a versao {#MyAppVersion}?' + #13#10#13#10 +
                'Seus dados e configuracoes serao preservados.',
                mbConfirmation, MB_YESNO) = IDNO then
      begin
        Result := False;
        Exit;
      end;

      // Tentar desinstalar versao anterior silenciosamente
      if RegQueryStringValue(HKLM,
        'Software\Microsoft\Windows\CurrentVersion\Uninstall\{{A1B2C3D4-E5F6-7890-ABCD-EF1234567890}_is1',
        'UninstallString', UninstallPath) then
      begin
        UninstallPath := RemoveQuotes(UninstallPath);
        if FileExists(UninstallPath) then
        begin
          Exec(UninstallPath, '/SILENT /NORESTART', '', SW_HIDE, ewWaitUntilTerminated, UninstallResult);
        end;
      end;
    end
    else
    begin
      // Mesma versao instalada
      if MsgBox('{#MyAppName} versao {#MyAppVersion} ja esta instalado.' + #13#10 +
                'Deseja reinstalar?',
                mbConfirmation, MB_YESNO) = IDNO then
      begin
        Result := False;
      end;
    end;
  end;
end;

// Verificar se o processo esta rodando antes de instalar
function PrepareToInstall(var NeedsRestart: Boolean): String;
var
  TaskKillResult: Integer;
begin
  Result := '';
  NeedsRestart := False;

  // Encerrar processo se estiver rodando
  if Exec(ExpandConstant('{sys}\taskkill.exe'), '/F /IM {#MyAppExeName}',
          '', SW_HIDE, ewWaitUntilTerminated, TaskKillResult) then
  begin
    // Aguardar processo encerrar
    Sleep(1500);
  end;
end;

// Pagina de boas-vindas personalizada
procedure InitializeWizard();
begin
  // Personalizar texto da pagina de boas-vindas
  WizardForm.WelcomeLabel1.Caption := 'Bem-vindo ao Assistente de Instalação do Registro Fácil!';
  WizardForm.WelcomeLabel2.Caption :=
    'Este assistente irá instalar o Registro Fácil ' + '{#MyAppVersion}' + ' no seu computador.' + #13#10 + #13#10 +
    'O Registro Fácil é um sistema completo de gestão de processos de cartório.' + #13#10 +
    'Roda localmente no seu computador, sem necessidade de internet.' + #13#10 + #13#10 +
    'Clique em Próximo para continuar ou em Cancelar para sair.';
  
  WizardForm.FinishedLabel.Caption :=
    'A instalação do Registro Fácil ' + '{#MyAppVersion}' + ' foi concluída com sucesso!' + #13#10 + #13#10 +
    'O sistema estará disponível no Menu Iniciar e, se selecionado, na Área de Trabalho.' + #13#10 + #13#10 +
    'Clique em Concluir para fechar este assistente.';
end;

// Acao apos desinstalacao concluida
procedure CurUninstallStepChanged(CurUninstallStep: TUninstallStep);
begin
  if CurUninstallStep = usDone then
  begin
    MsgBox(
      'O Registro Fácil foi desinstalado com sucesso.' + #13#10 + #13#10 +
      'IMPORTANTE: Seus dados foram mantidos em:' + #13#10 +
      ExpandConstant('{commonappdata}') + '\RegistroFacil' + #13#10 + #13#10 +
      'Para remover completamente, exclua essa pasta manualmente.',
      mbInformation, MB_OK
    );
  end;
end;
