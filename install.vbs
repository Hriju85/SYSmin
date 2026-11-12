' ThrottlerOS & SYSmin Windows Installer
Option Explicit
Dim sh, ret

Set sh = CreateObject("WScript.Shell")

On Error Resume Next
sh.Exec("python --version")
If Err.Number <> 0 Then
    MsgBox "Python was not found in PATH." & vbCrLf & vbCrLf & _
           "Please install Python 3.10+ from https://www.python.org" & vbCrLf & _
           "Be sure to check 'Add Python to PATH'.", vbCritical, "ThrottlerOS Setup"
    WScript.Quit 1
End If
On Error GoTo 0

ret = sh.Run("cmd /c pip install -r requirements.txt", 1, True)
If ret = 0 Then
    MsgBox "ThrottlerOS & SYSmin installed successfully!" & vbCrLf & vbCrLf & _
           "To start silently in the background, double-click run.vbs." & vbCrLf & _
           "The dashboard will be ready at http://127.0.0.1:8742", vbInformation, "ThrottlerOS Setup"
Else
    MsgBox "Installation completed with warnings. You can also run scripts\install.bat.", vbExclamation, "ThrottlerOS Setup"
End If

