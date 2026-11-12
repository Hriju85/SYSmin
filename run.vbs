' ThrottlerOS & SYSmin Silent Runner
Set WshShell = CreateObject("WScript.Shell")
WshShell.Run "pythonw -m backend.main --host 127.0.0.1 --port 8742", 0, False
