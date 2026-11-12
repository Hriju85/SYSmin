' ThrottlerOS Silent Launcher (No console window)
Set sh = CreateObject("WScript.Shell")
sh.Run "pythonw server.py --host 127.0.0.1 --port 8742", 0, False
