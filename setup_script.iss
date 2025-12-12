; Inno Setup Script for AutomateTools
; v1.3

[Setup]
; Cada aplicação deve ter um AppId único. Gere um novo em Tools -> Generate GUID no Inno Setup.
AppId={{BD09E837-8EAD-4106-B551-BA08B7B0FA3E}
AppName=AutomateTools
AppVersion=1.4
AppPublisher=Juan M. Lopes
DefaultDirName={autopf}\AutomateTools
DefaultGroupName=AutomateTools
DisableProgramGroupPage=yes
OutputBaseFilename=AutomateTools_Setup_v1.4
Compression=lzma
SolidCompression=yes
WizardStyle=modern

[Languages]
Name: "brazilianportuguese"; MessagesFile: "compiler:Languages\BrazilianPortuguese.isl"

[Tasks]
; Adiciona uma checkbox na instalação para criar um ícone na área de trabalho
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
; Esta é a linha principal: copia TODO o conteúdo da pasta gerada pelo PyInstaller
; para o diretório de instalação do usuário.
Source: "dist\AutomateTools\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "resources\mapeamento_programas.csv"; DestDir: "{app}"

; ATENÇÃO: Se suas ferramentas precisarem de dependências externas como o Ghostscript (para o Camelot),
; você precisaria incluir o instalador do Ghostscript aqui e executá-lo. Por enquanto, vamos focar
; na ferramenta de consolidação que não tem dependências externas.

[Icons]
; Ícone no Menu Iniciar
Name: "{group}\AutomateTools"; Filename: "{app}\AutomateTools.exe"
; Ícone na Área de Trabalho (se a task for selecionada)
Name: "{autodesktop}\AutomateTools"; Filename: "{app}\AutomateTools.exe"; Tasks: desktopicon

[Run]
; Oferece a opção de iniciar o programa ao final da instalação
Filename: "{app}\AutomateTools.exe"; Description: "{cm:LaunchProgram,AutomateTools}"; Flags: nowait postinstall skipifsilent