' AOJ Command OS — silent launcher (no console window)
' This VBScript is used by the Start Menu and Desktop shortcuts so the server
' starts without a black console window appearing.
'
' To stop AOJ Command OS, open Task Manager and end the python.exe process,
' or run: taskkill /F /IM python.exe /FI "WINDOWTITLE eq AOJ*"

Dim oShell
Set oShell = CreateObject("WScript.Shell")

Dim installDir
installDir = Left(WScript.ScriptFullName, InStrRev(WScript.ScriptFullName, "\"))

' Run launch.bat hidden
oShell.Run Chr(34) & installDir & "launch.bat" & Chr(34), 0, False

Set oShell = Nothing
