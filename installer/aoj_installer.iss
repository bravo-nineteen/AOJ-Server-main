; =============================================================================
; AOJ Command OS - Inno Setup Installer Script
; =============================================================================
; Build this installer with:
;   iscc installer\aoj_installer.iss
; Or use the helper script:
;   powershell -ExecutionPolicy Bypass -File installer\build_installer.ps1
;
; Requirements to BUILD:
;   - Inno Setup 6.x  (https://jrsoftware.org/isdl.php)
;
; Requirements to INSTALL:
;   - Windows 10 / 11 (64-bit)
;   - Python 3.11+    (https://python.org/downloads)
;   - Node.js 18+     (https://nodejs.org)
; =============================================================================

#define AppName      "AOJ Command OS"
#define AppVersion   "1.0.1"
#define AppVersionMajor      1
#define AppVersionMinor      0
#define AppVersionRevision   1
#define AppVersionBuild      0
#define AppPublisher "Airsoft Online Japan"
#define AppCreator   "is Nineteen"
#define AppURL       "https://github.com/bravo-nineteen/AOJ-Server"
#define AppExe       "AOJ Command OS.lnk"
#define AppGUID      "{{6F3A1D2B-84CE-4B7E-9031-F2C84A6D5E90}}"

[Setup]
AppId={#AppGUID}
AppName={#AppName}
AppVersion={#AppVersion}
AppVerName={#AppName} v{#AppVersion}
AppPublisher={#AppPublisher}
AppCopyright=(C) 2024-2026 {#AppPublisher}
AppPublisherURL={#AppURL}
AppSupportURL={#AppURL}/issues
AppUpdatesURL={#AppURL}/releases
DefaultDirName={autopf}\{#AppName}
DefaultGroupName={#AppName}
DisableProgramGroupPage=no
AllowNoIcons=no
CreateAppDir=yes
; Output
OutputDir=..\dist\installer
OutputBaseFilename=AOJ_CommandOS_Setup_v{#AppVersion}_x64
; Compression
Compression=lzma2/ultra64
SolidCompression=yes
; UI
WizardStyle=modern
WizardSizePercent=120
; Setup icon and branding — only set if asset files are present in the repo.
; Place aoj_icon.ico and aoj_logo.bmp in installer/assets/ to enable full branding.
#if FileExists(SourcePath + "assets\aoj_icon.ico")
SetupIconFile=assets\aoj_icon.ico
WizardSmallImageFile=assets\aoj_icon.ico
UninstallDisplayIcon={app}\assets\aoj_icon.ico
#endif
#if FileExists(SourcePath + "assets\aoj_logo.bmp")
WizardImageFile=assets\aoj_logo.bmp
#endif
; Privileges — needs admin to write to Program Files and run pip
PrivilegesRequired=admin
; Windows 10 minimum
MinVersion=10.0.17763
; Architecture
ArchitecturesAllowed=x64
ArchitecturesInstallIn64BitMode=x64
; Uninstaller
UninstallDisplayName={#AppName} v{#AppVersion}
VersionInfoCompany={#AppPublisher}
VersionInfoDescription={#AppName} Installer v{#AppVersion}
VersionInfoProductName={#AppName}
; Must be strictly numeric (major.minor.revision.build) for Windows version resources.
VersionInfoProductVersion={#AppVersionMajor}.{#AppVersionMinor}.{#AppVersionRevision}.{#AppVersionBuild}
VersionInfoVersion={#AppVersionMajor}.{#AppVersionMinor}.{#AppVersionRevision}.{#AppVersionBuild}
VersionInfoCopyright=(C) 2024-2026 {#AppPublisher}
; Installation upgrade behavior
AllowUNCPath=no
CloseApplications=force
CloseApplicationsFilter=*.exe,*.vbs
; After install, ask to launch
InfoAfterFile=..\installer\after_install.txt

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon";   Description: "Create a &desktop shortcut"
Name: "startupentry";  Description: "Launch AOJ on &Windows startup"

[Dirs]
Name: "{app}"
Name: "{app}\backend"
Name: "{app}\frontend"
Name: "{app}\scripts"
Name: "{app}\docs"
Name: "{app}\assets"

[Files]
; ---------- Backend (exclude venv, cache, database, test artifacts) ----------
Source: "..\backend\app\*";          DestDir: "{app}\backend\app";          Flags: ignoreversion recursesubdirs createallsubdirs; Excludes: "__pycache__,*.pyc,*.pyo"
Source: "..\backend\desktop_launcher.py"; DestDir: "{app}\backend";        Flags: ignoreversion
Source: "..\backend\requirements.txt"; DestDir: "{app}\backend";            Flags: ignoreversion
Source: "..\backend\README.md";      DestDir: "{app}\backend";              Flags: ignoreversion skipifsourcedoesntexist

; ---------- Frontend source (exclude built output and installed modules) ------
Source: "..\frontend\src\*";        DestDir: "{app}\frontend\src";          Flags: ignoreversion recursesubdirs createallsubdirs
Source: "..\frontend\public\*";     DestDir: "{app}\frontend\public";       Flags: ignoreversion recursesubdirs createallsubdirs skipifsourcedoesntexist
Source: "..\frontend\index.html";   DestDir: "{app}\frontend";              Flags: ignoreversion skipifsourcedoesntexist
Source: "..\frontend\vite.config.*"; DestDir: "{app}\frontend";             Flags: ignoreversion skipifsourcedoesntexist
Source: "..\frontend\package.json"; DestDir: "{app}\frontend";              Flags: ignoreversion
Source: "..\frontend\package-lock.json"; DestDir: "{app}\frontend";         Flags: ignoreversion skipifsourcedoesntexist

; ---------- Scripts ----------------------------------------------------------
Source: "..\scripts\install_windows.ps1";        DestDir: "{app}\scripts"; Flags: ignoreversion
Source: "..\scripts\start_production_windows.ps1"; DestDir: "{app}\scripts"; Flags: ignoreversion
Source: "..\scripts\start_backend_windows.ps1";  DestDir: "{app}\scripts"; Flags: ignoreversion
Source: "..\scripts\start_desktop_windows.ps1";  DestDir: "{app}\scripts"; Flags: ignoreversion

; ---------- Launcher helpers -------------------------------------------------
Source: "..\installer\launch.bat";  DestDir: "{app}";                       Flags: ignoreversion
Source: "..\installer\launch.vbs";  DestDir: "{app}";                       Flags: ignoreversion

; ---------- Docs & readme ----------------------------------------------------
Source: "..\README.md";             DestDir: "{app}";                       Flags: ignoreversion
Source: "..\docs\*";                DestDir: "{app}\docs";                  Flags: ignoreversion recursesubdirs createallsubdirs skipifsourcedoesntexist

; ---------- Optional icon asset ----------------------------------------------
Source: "..\installer\assets\aoj_icon.ico"; DestDir: "{app}\assets";        Flags: ignoreversion skipifsourcedoesntexist

[Icons]
; Start Menu
Name: "{group}\{#AppName}";                     Filename: "{app}\launch.vbs";   WorkingDir: "{app}"; IconFilename: "{app}\assets\aoj_icon.ico"; Comment: "Start AOJ Command OS - Tactical Server and Frontend"
Name: "{group}\Open in Browser";                Filename: "http://localhost:8000"; IconFilename: "{app}\assets\aoj_icon.ico"
Name: "{group}\Documentation";                  Filename: "{app}\README.md"; Comment: "View installation guide"
Name: "{group}\{cm:UninstallProgram,{#AppName}}"; Filename: "{uninstallexe}"

; Desktop
Name: "{autodesktop}\{#AppName}";               Filename: "{app}\launch.vbs";   WorkingDir: "{app}"; Tasks: desktopicon; IconFilename: "{app}\assets\aoj_icon.ico"; Comment: "Start AOJ Command OS - Tactical Server and Frontend"

; Startup
Name: "{userstartup}\{#AppName}";               Filename: "{app}\launch.vbs";   WorkingDir: "{app}"; Tasks: startupentry

[Run]
; Step 1 — install Python packages and build React frontend
Filename: "powershell.exe"; Parameters: "-ExecutionPolicy Bypass -NonInteractive -WindowStyle Normal -File ""{app}\scripts\install_windows.ps1"""; WorkingDir: "{app}"; StatusMsg: "Installing dependencies and building frontend (may take 2-5 minutes)..."; Flags: waituntilterminated

; Step 2 — offer to launch immediately after install
Filename: "wscript.exe"; Parameters: """{app}\launch.vbs"""; Description: "Launch {#AppName} now"; Flags: postinstall nowait skipifsilent

[UninstallRun]
; Stop any running instance before uninstall
Filename: "taskkill.exe"; Parameters: "/F /IM python.exe /FI ""WINDOWTITLE eq AOJ*"""; Flags: skipifdoesntexist; RunOnceId: "KillPython"

[UninstallDelete]
; Remove generated directories that the uninstaller won't otherwise clean up
Type: filesandordirs; Name: "{app}\backend\.venv"
Type: filesandordirs; Name: "{app}\backend\__pycache__"
Type: filesandordirs; Name: "{app}\frontend\node_modules"
Type: filesandordirs; Name: "{app}\frontend\dist"
Type: filesandordirs; Name: "{app}\backend\aoj_command_os.db"
Type: filesandordirs; Name: "{app}\backend\aoj.db"

[Code]
// ---------------------------------------------------------------------------
// Pre-install checks: Python 3.11+ and Node.js 18+
// ---------------------------------------------------------------------------

function CheckPython(): Boolean;
var
  ResultCode: Integer;
begin
  Result := False;
  // Try 'py -3 --version'
  if Exec('py', '-3 --version', '', SW_HIDE, ewWaitUntilTerminated, ResultCode) then
    if ResultCode = 0 then begin Result := True; Exit; end;
  // Try 'python --version'
  if Exec('python', '--version', '', SW_HIDE, ewWaitUntilTerminated, ResultCode) then
    if ResultCode = 0 then begin Result := True; Exit; end;
end;

function CheckNode(): Boolean;
var
  ResultCode: Integer;
begin
  Result := False;
  if Exec('node', '--version', '', SW_HIDE, ewWaitUntilTerminated, ResultCode) then
    if ResultCode = 0 then Result := True;
end;

function InitializeSetup(): Boolean;
var
  Missing: String;
begin
  Missing := '';
  if not CheckPython() then
    Missing := Missing + #13#10 + '  - Python 3.11+  (https://python.org/downloads)';
  if not CheckNode() then
    Missing := Missing + #13#10 + '  - Node.js 18+   (https://nodejs.org)';

  if Missing <> '' then begin
    MsgBox(
      'AOJ Command OS requires the following software to be installed first:' +
      Chr(13)+Chr(10) + Missing + Chr(13)+Chr(10)+Chr(13)+Chr(10) +
      'Please install the missing software and re-run this installer.',
      mbError, MB_OK
    );
    Result := False;
  end else
    Result := True;
end;
