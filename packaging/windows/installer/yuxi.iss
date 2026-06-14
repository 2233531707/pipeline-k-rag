#define AppName "地下管网知识模型数据库"
#define AppVersion "2.0.0-rc"
#define AppPublisher "Pipeline-K-RAG"

[Setup]
AppId={{D15C012E-7B56-4E8E-B9CA-C2C349E63312}
AppName={#AppName}
AppVersion={#AppVersion}
AppPublisher={#AppPublisher}
DefaultDirName={autopf}\Yuxi Desktop
DefaultGroupName={#AppName}
OutputDir=..\dist
OutputBaseFilename=Yuxi-Desktop-Setup
Compression=lzma2
SolidCompression=yes
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
PrivilegesRequired=admin
DisableProgramGroupPage=yes
UninstallDisplayIcon={app}\YuxiDesktopLauncher.exe
WizardStyle=modern

[Files]
Source: "..\dist\launcher\YuxiDesktopLauncher.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\bundle\app\*"; DestDir: "{app}\app"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "..\bundle\images\*"; DestDir: "{app}\images"; Flags: ignoreversion recursesubdirs createallsubdirs skipifsourcedoesntexist

[Icons]
Name: "{autoprograms}\{#AppName}"; Filename: "{app}\YuxiDesktopLauncher.exe"; Parameters: "--project-dir ""{app}\app"""
Name: "{autodesktop}\{#AppName}"; Filename: "{app}\YuxiDesktopLauncher.exe"; Parameters: "--project-dir ""{app}\app"""; Tasks: desktopicon

[Tasks]
Name: "desktopicon"; Description: "创建桌面快捷方式"; GroupDescription: "附加图标："

[Run]
Filename: "{app}\YuxiDesktopLauncher.exe"; Parameters: "--project-dir ""{app}\app"""; Description: "启动 {#AppName}"; Flags: nowait postinstall skipifsilent

[UninstallDelete]
Type: filesandordirs; Name: "{app}\build"

[Code]
function InitializeSetup(): Boolean;
begin
  Result := True;
end;
