[Setup]
AppName=Nota Çevirici
AppVersion=1.0.3
AppPublisher=Nota Çevirici
DefaultDirName={autopf}\NotaCevirici
DefaultGroupName=Nota Çevirici
OutputDir=installer_output
OutputBaseFilename=NotaCevirici-Kurulum
Compression=lzma2
SolidCompression=yes
ArchitecturesInstallIn64BitMode=x64compatible
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog
UninstallDisplayName=Nota Çevirici

[Languages]
Name: "turkish"; MessagesFile: "compiler:Languages\Turkish.isl"

[Tasks]
Name: "desktopicon"; Description: "Masaüstüne kısayol oluştur"; Flags: unchecked

[Files]
Source: "dist\NotaCevirici\*"; DestDir: "{app}"; Flags: recursesubdirs ignoreversion

[Icons]
Name: "{group}\Nota Çevirici"; Filename: "{app}\NotaCevirici.exe"
Name: "{autodesktop}\Nota Çevirici"; Filename: "{app}\NotaCevirici.exe"; Tasks: desktopicon

[Run]
Filename: "{app}\NotaCevirici.exe"; Description: "Nota Çevirici'yi başlat"; Flags: nowait postinstall skipifsilent
