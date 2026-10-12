[Setup]
AppName=Variance Studio
AppVersion=1.0.0
DefaultDirName={autopf}\VarianceStudio
DefaultGroupName=Variance Studio
OutputBaseFilename=VarianceStudio-Setup
OutputDir=installer_output

[Files]
Source: "backend\dist\VarianceStudio\*"; DestDir: "{app}"; Flags: recursesubdirs

[Icons]
Name: "{group}\Variance Studio"; Filename: "{app}\VarianceStudio.exe"
Name: "{autodesktop}\Variance Studio"; Filename: "{app}\VarianceStudio.exe"