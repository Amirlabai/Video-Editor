; Inno Setup script for ffmpegMagic
; Requires PyInstaller output in installer_files_{version}/ffmpegMagic.exe

#define MyAppName "ffmpegMagic"
#define MyAppExeName "ffmpegMagic.exe"
#define MyAppPublisher "Amir Labai"
#define MyAppURL "https://github.com/Amirlabai/Video-Editor/releases/latest"
#define MyAppUpdatesURL "https://github.com/Amirlabai/Video-Editor/releases/latest"

[Setup]
AppId={{A1B2C3D4-E5F6-7890-ABCD-EF1234567890}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
AppUpdatesURL={#MyAppUpdatesURL}
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
OutputDir=installers
OutputBaseFilename=ffmpegMagic_Setup_{#MyAppVersion}
Compression=lzma2
SolidCompression=yes
WizardStyle=modern

; PyInstaller one-folder output: ..\installer_files_{version}\ffmpegMagic\

[Files]
Source: "..\installer_files_{#MyAppVersion}\{#MyAppName}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "Launch {#MyAppName}"; Flags: nowait postinstall skipifsilent
