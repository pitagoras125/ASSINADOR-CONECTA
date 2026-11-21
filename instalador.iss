#define MyAppName "Conecta PDF"
#define TermsHash "8c99aee48516c431550b62e30b707e3ff00c19cfda0afcbc22dc166c6de8aaae"
[Setup]
LicenseFile=TERMOS.txt
AppId={{0839D786-4D38-48F4-8332-244156A27CDA}
AppName={#MyAppName}
AppVersion=1.3.0
DefaultDirName={localappdata}\Programs\AssinadorConecta
DefaultGroupName={#MyAppName}
PrivilegesRequired=lowest
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
OutputDir=Output
OutputBaseFilename=Instalar_Conecta_PDF_1.3.0
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
AppPublisher=AVANTE SISTEMAS LTDA
CloseApplications=yes
RestartApplications=no
VersionInfoVersion=1.3.0.0
ChangesAssociations=yes
SetupIconFile=assets\app_icon.ico
UninstallDisplayIcon={app}\AssinadorConecta.exe
[Languages]
Name: "brazilianportuguese"; MessagesFile: "compiler:Languages\BrazilianPortuguese.isl"
[Files]
Source: "TERMOS.txt"; DestDir: "{app}"
Source: "dist\AssinadorConecta\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "LEIA-ME.md"; DestDir: "{app}"
Source: "AVISOS-DE-LICENCAS.md"; DestDir: "{app}"
[Tasks]
Name: "desktopicon"; Description: "Criar atalho na Area de Trabalho"; Flags: unchecked
[Icons]
Name: "{autoprograms}\Conecta PDF"; Filename: "{app}\AssinadorConecta.exe"
Name: "{autodesktop}\Conecta PDF"; Filename: "{app}\AssinadorConecta.exe"; Tasks: desktopicon
[Registry]
Root: HKCU; Subkey: "Software\Conecta\PDF\Installer"; ValueType: string; ValueName: "AcceptedTerms"; ValueData: "{#TermsHash}"; Flags: uninsdeletekey
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.pdf\shell\AssinadorConecta"; ValueType: string; ValueData: "Assinar com Conecta"; Flags: uninsdeletekey
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.pdf\shell\AssinadorConecta\command"; ValueType: string; ValueData: """{app}\AssinadorConecta.exe"" ""%1"""
Root: HKCU; Subkey: "Software\Classes\Conecta.PDF"; ValueType: string; ValueData: "Documento PDF"; Flags: uninsdeletekey
Root: HKCU; Subkey: "Software\Classes\Conecta.PDF\DefaultIcon"; ValueType: string; ValueData: "{app}\AssinadorConecta.exe,0"
Root: HKCU; Subkey: "Software\Classes\Conecta.PDF\shell\open\command"; ValueType: string; ValueData: """{app}\AssinadorConecta.exe"" ""%1"""
Root: HKCU; Subkey: "Software\Classes\Conecta.PDF\shell\print\command"; ValueType: string; ValueData: """{app}\AssinadorConecta.exe"" --print ""%1"""
Root: HKCU; Subkey: "Software\Classes\.pdf\OpenWithProgids"; ValueType: none; ValueName: "Conecta.PDF"; Flags: uninsdeletevalue
Root: HKCU; Subkey: "Software\Conecta\Assinador\Capabilities\FileAssociations"; ValueType: string; ValueName: ".pdf"; ValueData: "Conecta.PDF"; Flags: uninsdeletevalue
Root: HKCU; Subkey: "Software\Classes\Conecta.NFe55"; ValueType: string; ValueData: "NF-e modelo 55"; Flags: uninsdeletekey
Root: HKCU; Subkey: "Software\Classes\Conecta.NFe55\DefaultIcon"; ValueType: string; ValueData: "{app}\AssinadorConecta.exe,0"
Root: HKCU; Subkey: "Software\Classes\Conecta.NFe55\shell\open\command"; ValueType: string; ValueData: """{app}\AssinadorConecta.exe"" ""%1"""
Root: HKCU; Subkey: "Software\Classes\.xml\OpenWithProgids"; ValueType: none; ValueName: "Conecta.NFe55"; Flags: uninsdeletevalue
Root: HKCU; Subkey: "Software\Conecta\Assinador\Capabilities\FileAssociations"; ValueType: string; ValueName: ".xml"; ValueData: "Conecta.NFe55"; Flags: uninsdeletevalue
Root: HKCU; Subkey: "Software\Conecta\Assinador\Capabilities"; ValueType: string; ValueName: "ApplicationName"; ValueData: "Conecta PDF"; Flags: uninsdeletekey
Root: HKCU; Subkey: "Software\Conecta\Assinador\Capabilities"; ValueType: string; ValueName: "ApplicationDescription"; ValueData: "Leitor PDF e XML NF-e modelo 55, com assinatura de documentos."
Root: HKCU; Subkey: "Software\RegisteredApplications"; ValueType: string; ValueName: "Conecta PDF"; ValueData: "Software\Conecta\Assinador\Capabilities"; Flags: uninsdeletevalue
[Run]
Filename: "{app}\AssinadorConecta.exe"; Description: "Abrir Conecta PDF"; Flags: nowait postinstall skipifsilent

[Code]
function InitializeSetup(): Boolean;
var
  Accepted: String;
begin
  Result := True;
  if WizardSilent then
    Result := RegQueryStringValue(HKCU, 'Software\Conecta\PDF\Installer', 'AcceptedTerms', Accepted)
      and (Accepted = '{#TermsHash}');
end;
