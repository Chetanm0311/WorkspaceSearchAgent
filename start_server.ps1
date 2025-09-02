#!/usr/bin/env pwsh
Set-Location "C:\Users\cshriram\OneDrive - Intel Corporation\Desktop\WorkSpaceAgent"
.\venv\Scripts\Activate.ps1
python -m uvicorn main:app --host 127.0.0.1 --port 8000 --log-level info

