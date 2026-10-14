#ifndef AppVersion
  #define AppVersion "0.2.0b1"
#endif
#ifndef AppNumericVersion
  #define AppNumericVersion "0.2.0.0"
#endif
[Setup]
AppId={{D7474072-9006-45D3-AD1B-8457879F216A}
AppName=Document Studio
AppVersion={#AppVersion}
VersionInfoVersion={#AppNumericVersion}
AppPublisher=Document Studio contributors
DefaultDirName={localappdata}\Programs\Document Studio
DefaultGroupName=Document Studio
UsePreviousAppDir=yes
UsePreviousGroup=yes
UsePreviousTasks=yes
AppMutex=Local\DocumentStudio-D7474072-9006-45D3-AD1B-8457879F216A
CloseApplications=yes
RestartApplications=no
AppComments=Personal settings and credentials are preserved on upgrade and uninstall.
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
#ifdef LifecycleFault
; Test-only: fail on a deliberately missing external payload during installation.
; The fault build is never placed in Release assets.
Source: "..\dist\DocumentStudio\DocumentStudio.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "{tmp}\DocumentStudio-Injected-Missing-Payload.bin"; DestDir: "{app}"; Flags: external ignoreversion; ExternalSize: 1
#endif
Source: "..\dist\DocumentStudio\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
[Icons]
Name: "{group}\Document Studio"; Filename: "{app}\DocumentStudio.exe"
Name: "{autodesktop}\Document Studio"; Filename: "{app}\DocumentStudio.exe"; Tasks: desktopicon
[Run]
Filename: "{app}\DocumentStudio.exe"; Description: "Launch Document Studio"; Flags: nowait postinstall skipifsilent

; No user data or Credential Manager entries are installed or uninstalled here.
[Code]
function PrepareToInstall(var NeedsRestart: Boolean): String;
var AppPath, DataPath: String;
begin
  AppPath := Lowercase(AddBackslash(ExpandConstant('{app}')));
  DataPath := Lowercase(AddBackslash(ExpandConstant('{localappdata}\DocumentStudio')));
  if (Pos(AppPath, DataPath) = 1) or (Pos(DataPath, AppPath) = 1) then
    Result := 'Program files must be separate from the DocumentStudio personal data directory.'
  else
    Result := '';
end;

