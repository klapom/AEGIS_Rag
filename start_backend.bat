@echo off
cd /d "C:\Users\Klaus Pommer\OneDrive - Pommer IT-Consulting GmbH\99_Studium_Klaus\AEGIS_Rag"
start /B poetry run uvicorn src.api.main:app --host 0.0.0.0 --port 8000
timeout /t 2 /nobreak > nul
