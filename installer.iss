; Q 수치 계산기 설치 프로그램 (Inno Setup 6)
; 빌드: ISCC.exe installer.iss  ->  installer_output\QNumberCalc-Setup.exe
#define MyAppName "Q 수치 계산기"
#define MyAppExeName "QNumberCalc.exe"
#define MyAppVersion "1.0.0"

[Setup]
AppId={{D1D7F19C-E10E-482D-8B93-7EACEDE89334}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher=Q Number Calculator
; 관리자 권한 없이 내 계정에만 설치 (회사 PC에서도 설치 가능)
PrivilegesRequired=lowest
DefaultDirName={autopf}\QNumberCalc
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=yes
OutputDir=installer_output
OutputBaseFilename=QNumberCalc-Setup
SetupIconFile=assets\icon.ico
UninstallDisplayIcon={app}\QNumberCalc.exe
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
UninstallDisplayName={#MyAppName}
; 설치 끝에 윈도우가 아이콘을 다시 읽게 한다 (바탕화면/시작메뉴에 옛 아이콘이 남는 현상 방지)
ChangesAssociations=yes
ArchitecturesInstallIn64BitMode=x64compatible

[Languages]
#if FileExists(CompilerPath + "Languages\Korean.isl")
Name: "korean"; MessagesFile: "compiler:Languages\Korean.isl"
#else
Name: "english"; MessagesFile: "compiler:Default.isl"
#endif

[Tasks]
Name: "desktopicon"; Description: "바탕화면에 바로가기 만들기"; GroupDescription: "추가 작업:"

[Files]
Source: "dist\QNumberCalc\*"; DestDir: "{app}"; Flags: recursesubdirs createallsubdirs ignoreversion
; 바로가기 전용 아이콘 파일 (바탕화면이 옛 아이콘 기억을 쓰지 않도록 새 이름으로 따로 둔다)
Source: "assets\icon.ico"; DestDir: "{app}"; DestName: "QCalc.ico"; Flags: ignoreversion

[Icons]
Name: "{autoprograms}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; IconFilename: "{app}\QCalc.ico"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; IconFilename: "{app}\QCalc.ico"; Tasks: desktopicon

[Registry]
; 프로그램 설정과 계산 기록은 제거할 때 함께 지운다
Root: HKCU; Subkey: "Software\QNumberCalc"; Flags: uninsdeletekey

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "설치가 끝나면 바로 실행"; Flags: nowait postinstall skipifsilent
