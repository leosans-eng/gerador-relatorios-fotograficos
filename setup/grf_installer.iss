; Inno Setup — versão lida de main.py via /DMyAppVersion=...
; Compile com: setup\grf_installer.bat

#ifndef MyAppVersion
  #define MyAppVersion "Erro na versão, contatar suporte"
#endif

#define MyAppName "Gerador de Relatórios Fotográficos"
#define MyAppFolder "GeradorRelatoriosFotograficos"
#define MyAppExeName "GeradorRelatoriosFotograficos.exe"
#define MyAppPublisher "Léo Santos"
#define MyAppURL "https://github.com/leosans-eng/gerador-relatorios-fotograficos"

[Setup]
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppVerName={#MyAppName} {#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
AppUpdatesURL={#MyAppURL}
DefaultDirName=C:\GeradorRelatoriosFotograficos
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=yes
LicenseFile=

OutputDir=..\dist
OutputBaseFilename=GeradorRelatoriosFotograficos_Setup_{#MyAppVersion}
SetupIconFile=icone.ico
UninstallDisplayIcon={app}\{#MyAppExeName}

Compression=lzma2/ultra64
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=lowest
ArchitecturesInstallIn64BitMode=x64compatible

VersionInfoCompany={#MyAppPublisher}
VersionInfoDescription=Instalador do Gerador de Relatorios Fotograficos
VersionInfoCopyright=© 2026 {#MyAppPublisher}

[Languages]
Name: "brazilianportuguese"; MessagesFile: "compiler:Languages\BrazilianPortuguese.isl"

[Tasks]
Name: "desktopicon"; Description: "Criar atalho na área de trabalho"; GroupDescription: "Atalhos:"

[Files]
Source: "..\dist\{#MyAppFolder}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
; Dados do usuário (condominios.json, imagens\) ficam na pasta de instalação após o primeiro uso.

[Dirs]
Name: "{app}\imagens"

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "Abrir {#MyAppName}"; Flags: nowait postinstall skipifsilent
