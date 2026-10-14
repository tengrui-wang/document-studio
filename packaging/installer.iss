#ifndef AppVersion
  #define AppVersion "0.1.0"
#endif
[Setup]
AppId={{D7474072-9006-45D3-AD1B-8457879F216A}
AppName=Document Studio
AppVersion={#AppVersion}
AppPublisher=Document Studio contributors
DefaultDirName={localappdata}\Programs\Document Studio
DefaultGroupName=Document Studio
PrivilegesRequired=lowest
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
OutputDir=..\release
OutputBaseFilename=DocumentStudio-{#AppVersion}-Setup
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
LicenseFile=..\LICENSE
UninstallDisplayIcon={app}\DocumentStudio.exe
[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"
[Tasks]
Name: "desktopicon"; Description: "Create a desktop shortcut"; Flags: unchecked
[Files]
Source: "..\dist\DocumentStudio\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
[Icons]
Name: "{group}\Document Studio"; Filename: "{app}\DocumentStudio.exe"
Name: "{autodesktop}\Document Studio"; Filename: "{app}\DocumentStudio.exe"; Tasks: desktopicon
[Run]
Filename: "{app}\DocumentStudio.exe"; Description: "Launch Document Studio"; Flags: nowait postinstall skipifsilent
