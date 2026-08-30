@echo off
rem scoreflow launcher: PDF -> MusicXML (HOMR) -> note-group feature analysis
rem usage: start.bat [pdf-or-dir] [options]
setlocal
set PY=D:\HOMR\homr-main\python_embed\python.exe
if not exist "%PY%" (
    echo [ERROR] python not found: %PY%
    echo Edit this file and set PY to your HOMR embedded python.
    exit /b 1
)
"%PY%" "%~dp0run.py" %*
exit /b %ERRORLEVEL%
