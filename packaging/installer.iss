#define AppVersion "0.7.0"
[Setup]
AppId={{633052C9-682C-49A0-A822-46796182285F}
AppName=Astra Video Editor
AppVersion={#AppVersion}
DefaultDirName={localappdata}\Programs\Astra Video Editor
PrivilegesRequired=lowest
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
OutputDir=..\artifacts
OutputBaseFilename=AstraVideoEditor-setup-candidate
Compression=lzma2
SolidCompression=yes
UninstallDisplayIcon={app}\AstraVideoEditor.exe
[Files]
Source: "..\artifacts\portable\AstraVideoEditor\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
[Icons]
Name: "{userprograms}\Astra Video Editor"; Filename: "{app}\AstraVideoEditor.exe"
