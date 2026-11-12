' ThrottlerOS Windows One-Click Installer
Option Explicit
Dim sh, ret

Set sh = CreateObject("WScript.Shell")

On Error Resume Next
sh.Exec("python --version")
If Err.Number <> 0 Then
    MsgBox "Python was not found on your system." & vbCrLf & vbCrLf & _
           "Please download and install Python 3.10 or newer from https://www.python.org" & vbCrLf & _
           "Ensure 'Add Python to PATH' is checked during installation.", vbCritical, "ThrottlerOS Setup"
    WScript.Quit 1
End If
On Error GoTo 0

ret = sh.Run("cmd /c pip install -r requirements.txt", 1, True)
If ret = 0 Then
    MsgBox "ThrottlerOS installation successful!" & vbCrLf & vbCrLf & _
           "To start ThrottlerOS silently in the background, double-click 'run.vbs'." & vbCrLf & _
           "The dashboard will open at http://127.0.0.1:8742", vbInformation, "ThrottlerOS Setup"
Else
    MsgBox "Installation encountered warnings or errors." & vbCrLf & _
           "Try running install.bat as Administrator.", vbExclamation, "ThrottlerOS Setup"
End If
