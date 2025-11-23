' Silent Launcher for LINE Homeroom Bot Scheduler Service
' This VBScript runs the batch file completely hidden (no window)
' Perfect for startup - runs completely in background

Set WshShell = CreateObject("WScript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")

' Get the directory where this VBS file is located
scriptPath = fso.GetParentFolderName(WScript.ScriptFullName)
batFile = scriptPath & "\run_scheduler_service.bat"

' Run the batch file completely hidden (0 = hidden window, False = don't wait)
WshShell.Run """" & batFile & """", 0, False

Set WshShell = Nothing
Set fso = Nothing
