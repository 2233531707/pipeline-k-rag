#define AppName "地下管网知识模型数据库"
#define AppVersion "2.0.0-rc"
#define AppPublisher "Pipeline-K-RAG"
#define LauncherName "地下管网知识模型数据库启动器.exe"

[Setup]
AppId={{D15C012E-7B56-4E8E-B9CA-C2C349E63312}
AppName={#AppName}
AppVersion={#AppVersion}
AppPublisher={#AppPublisher}
DefaultDirName={localappdata}\{#AppName}
DefaultGroupName={#AppName}
OutputDir=..\dist
OutputBaseFilename={#AppName}
Compression=lzma2
SolidCompression=yes
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
PrivilegesRequired=lowest
DisableProgramGroupPage=yes
UninstallDisplayIcon={app}\{#LauncherName}
WizardStyle=modern

[Files]
Source: "..\dist\launcher\YuxiDesktopLauncher.exe"; DestDir: "{app}"; DestName: "{#LauncherName}"; Flags: ignoreversion
Source: "..\bundle\backend.zip"; DestDir: "{tmp}"; Flags: ignoreversion deleteafterinstall
Source: "..\bundle\docker.zip"; DestDir: "{tmp}"; Flags: ignoreversion deleteafterinstall
Source: "..\bundle\web.zip"; DestDir: "{tmp}"; Flags: ignoreversion deleteafterinstall
Source: "..\bundle\app\.dockerignore"; DestDir: "{app}\app"; Flags: ignoreversion
Source: "..\bundle\app\.env.template"; DestDir: "{app}\app"; Flags: ignoreversion
Source: "..\bundle\app\docker-compose.desktop.yml"; DestDir: "{app}\app"; Flags: ignoreversion
Source: "..\bundle\app\LICENSE"; DestDir: "{app}\app"; Flags: ignoreversion
Source: "..\bundle\app\README.md"; DestDir: "{app}\app"; Flags: ignoreversion
Source: "..\bundle\images\*"; DestDir: "{app}\images"; Flags: ignoreversion recursesubdirs createallsubdirs skipifsourcedoesntexist
Source: "..\地下管网知识模型数据库-使用教程.txt"; DestDir: "{app}"; Flags: ignoreversion

[Dirs]
Name: "{app}\app\backend\test"
Name: "{app}\app\docker\volumes\yuxi"
Name: "{app}\app\docker\volumes\models"
Name: "{app}\app\docker\volumes\neo4j\data"
Name: "{app}\app\docker\volumes\neo4j\logs"
Name: "{app}\app\docker\volumes\milvus\etcd"
Name: "{app}\app\docker\volumes\milvus\minio"
Name: "{app}\app\docker\volumes\milvus\minio_config"
Name: "{app}\app\docker\volumes\milvus\milvus"
Name: "{app}\app\docker\volumes\milvus\logs"
Name: "{app}\app\docker\volumes\redis"
Name: "{app}\app\docker\volumes\paddlex"

[Icons]
Name: "{autoprograms}\{#AppName}"; Filename: "{app}\{#LauncherName}"; Parameters: "--project-dir ""{app}\app"""
Name: "{autoprograms}\使用教程"; Filename: "{app}\地下管网知识模型数据库-使用教程.txt"
Name: "{autodesktop}\{#AppName}"; Filename: "{app}\{#LauncherName}"; Parameters: "--project-dir ""{app}\app"""; Tasks: desktopicon

[Tasks]
Name: "desktopicon"; Description: "创建桌面快捷方式"; GroupDescription: "附加图标："

[Run]
Filename: "{sys}\WindowsPowerShell\v1.0\powershell.exe"; Parameters: "-NoProfile -ExecutionPolicy Bypass -Command ""Expand-Archive -LiteralPath '{tmp}\backend.zip' -DestinationPath '{app}\app' -Force"""; Flags: runhidden waituntilterminated
Filename: "{sys}\WindowsPowerShell\v1.0\powershell.exe"; Parameters: "-NoProfile -ExecutionPolicy Bypass -Command ""Expand-Archive -LiteralPath '{tmp}\docker.zip' -DestinationPath '{app}\app' -Force"""; Flags: runhidden waituntilterminated
Filename: "{sys}\WindowsPowerShell\v1.0\powershell.exe"; Parameters: "-NoProfile -ExecutionPolicy Bypass -Command ""Expand-Archive -LiteralPath '{tmp}\web.zip' -DestinationPath '{app}\app' -Force"""; Flags: runhidden waituntilterminated
Filename: "{app}\{#LauncherName}"; Parameters: "--project-dir ""{app}\app"""; Description: "启动 {#AppName}"; Flags: nowait postinstall skipifsilent

[UninstallDelete]
Type: filesandordirs; Name: "{app}\build"

[Code]
function InitializeSetup(): Boolean;
begin
  Result := True;
end;
