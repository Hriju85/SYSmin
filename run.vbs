' ==============================================================================
' SYSmin All-In-One Unified Controller (Windows VBScript)
' Runs executable / python backend silently, manages lifecycle, and opens browser
' ==============================================================================
Option Explicit

Dim fso, WshShell, scriptDir, pidFile
Set fso = CreateObject("Scripting.FileSystemObject")
Set WshShell = CreateObject("WScript.Shell")

scriptDir = fso.GetParentFolderName(WScript.ScriptFullName)
WshShell.CurrentDirectory = scriptDir
pidFile = scriptDir & "\.server.pid"

' Helper to check if HTTP endpoint is responding on port 8000
Function CheckPortReady(url)
    On Error Resume Next
    Dim http
    Set http = CreateObject("MSXML2.ServerXMLHTTP.6.0")
    If Err.Number <> 0 Then Set http = CreateObject("MSXML2.ServerXMLHTTP")
    If Err.Number <> 0 Then Set http = CreateObject("Microsoft.XMLHTTP")
    http.setTimeouts 400, 400, 400, 400
    http.open "GET", url, False
    http.send
    If Err.Number = 0 And (http.status = 200 Or http.status = 304) Then
        CheckPortReady = True
    Else
        CheckPortReady = False
    End If
    On Error GoTo 0
End Function

' Subroutine to cleanly stop SYSmin server processes
Sub StopSysmin()
    On Error Resume Next
    ' 1. Terminate PID from .server.pid
    If fso.FileExists(pidFile) Then
        Dim ts, pidStr, pid
        Set ts = fso.OpenTextFile(pidFile, 1)
        pidStr = Trim(ts.ReadAll)
        ts.Close
        If IsNumeric(pidStr) Then
            pid = CLng(pidStr)
            If pid > 0 Then WshShell.Run "taskkill.exe /F /PID " & pid, 0, True
        End If
        fso.DeleteFile pidFile, True
    End If

    ' 2. Terminate matching process by name and commandline
    Dim objWMIService, colProcesses, objProcess, cmdLine
    Set objWMIService = GetObject("winmgmts:\\.\root\cimv2")
    Set colProcesses = objWMIService.ExecQuery("SELECT ProcessId, Name, CommandLine FROM Win32_Process")
    For Each objProcess In colProcesses
        cmdLine = LCase(objProcess.CommandLine & "")
        If InStr(cmdLine, "processcontroller") > 0 Or _
           (InStr(cmdLine, LCase(scriptDir)) > 0 And InStr(cmdLine, "main.py") > 0) Then
            objProcess.Terminate()
        End If
    Next

    ' 3. Free port 8000
    WshShell.Run "cmd.exe /c ""for /f ""tokens=5"" %a in ('netstat -aon ^| findstr :8000 ^| findstr LISTENING') do taskkill.exe /F /PID %a""", 0, True
    On Error GoTo 0
End Sub

' 1. If already running on port 8000: prompt user to open or stop
If CheckPortReady("http://127.0.0.1:8000/api/privacy") Then
    Dim choice
    choice = MsgBox("SYSmin is currently running on http://127.0.0.1:8000." & vbCrLf & vbCrLf & _
                    "• Click YES to open the dashboard in your default browser." & vbCrLf & _
                    "• Click NO to stop the background SYSmin process." & vbCrLf & _
                    "• Click CANCEL to exit without making changes.", 35, "SYSmin Controller")
    If choice = 6 Then ' vbYes
        WshShell.Run "http://127.0.0.1:8000", 1, False
        WScript.Quit 0
    ElseIf choice = 7 Then ' vbNo
        StopSysmin()
        WshShell.Popup "SYSmin server has been stopped.", 2, "SYSmin", 64
        WScript.Quit 0
    Else
        WScript.Quit 0
    End If
End If

' 2. Locate standalone executable or run from Python environment
Dim exePath, exeList, candidate, foundExe
foundExe = ""
exeList = Array(scriptDir & "\ProcessController.exe", scriptDir & "\dist\ProcessController.exe", scriptDir & "\SYSmin.exe")

For Each candidate In exeList
    If fso.FileExists(candidate) Then
        foundExe = candidate
        Exit For
    End If
Next

If foundExe <> "" Then
    ' Launch standalone EXE silently
    WshShell.Run Chr(34) & foundExe & Chr(34), 0, False
Else
    ' Fall back to Python source: check or setup .venv
    Dim venvDir, pythonwExe, pipExe, reqFile, mainPy
    venvDir = scriptDir & "\.venv"
    pythonwExe = venvDir & "\Scripts\pythonw.exe"
    pipExe = venvDir & "\Scripts\pip.exe"
    reqFile = scriptDir & "\requirements.txt"
    mainPy = scriptDir & "\backend\main.py"

    If Not fso.FolderExists(venvDir) Or Not fso.FileExists(pythonwExe) Then
        Dim setupCmd, exitCode
        setupCmd = "cmd.exe /c ""title SYSmin Setup && cd /d """ & scriptDir & """ && " & _
                   "echo Setting up Python environment and dependencies... && " & _
                   "(py -3 -m venv .venv 2>nul || python -m venv .venv) && " & _
                   ".venv\Scripts\pip.exe install -r """ & reqFile & """"""
        exitCode = WshShell.Run(setupCmd, 1, True)
        If exitCode <> 0 Or Not fso.FileExists(pythonwExe) Then
            MsgBox "Failed to set up Python virtual environment." & vbCrLf & _
                   "Please ensure Python 3 is installed with 'Add python.exe to PATH' enabled.", 16, "SYSmin Setup Error"
            WScript.Quit 1
        End If
    End If

    ' Launch main.py via pythonw.exe completely hidden
    WshShell.Run Chr(34) & pythonwExe & Chr(34) & " """ & mainPy & """", 0, False
End If

' 3. Wait for port 8000 to become ready (up to 25s)
Dim retries, isReady
retries = 0
isReady = False

Do While retries < 50
    WScript.Sleep 500
    retries = retries + 1
    If CheckPortReady("http://127.0.0.1:8000/api/privacy") Then
        isReady = True
        Exit Do
    End If
Loop

' 4. Open dashboard in default browser
WshShell.Run "http://127.0.0.1:8000", 1, False

