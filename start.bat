@echo off
setlocal enabledelayedexpansion
chcp 65001 >nul
title CANTINE SYSTEM - STARTUP

REM ================================
REM CONFIGURATION
REM ================================
set ROOT_DIR=C:\CANTINESYSTEM
set BACKEND_DIR=%ROOT_DIR%\api_cantine
set FRONTEND_DIR=%ROOT_DIR%\cantine_front

set PYTHON=%BACKEND_DIR%\.venv\Scripts\python.exe
set BACKEND_HOST=127.0.0.1
set BACKEND_PORT=8000
set BACKEND_CHECK_URL=http://%BACKEND_HOST%:%BACKEND_PORT%/api/guichets/

set FRONTEND_PORT=3000

echo.
echo =========================================
echo   DEMARRAGE DU SYSTEME CANTINE
echo =========================================
echo.

REM ================================
REM START DJANGO BACKEND
REM ================================
echo [INFO] Lancement du backend Django...

pushd %BACKEND_DIR%
start "" /B "%PYTHON%" manage.py runserver %BACKEND_HOST%:%BACKEND_PORT% --noreload
popd

REM ================================
REM WAIT BACKEND READY
REM ================================
echo [INFO] Verification de la disponibilite de l’API...

set READY=0
for /L %%i in (1,1,30) do (
    timeout /t 1 >nul
    curl -s "%BACKEND_CHECK_URL%" >nul 2>&1
    if !errorlevel! == 0 (
        set READY=1
        goto BACKEND_OK
    )
)

:BACKEND_OK
if %READY%==0 (
    echo [ERREUR] Backend Django indisponible apres 30s.
    echo [ERREUR] Frontend non lance.
    exit /b 1
)

echo [OK] Backend Django operationnel.
echo.

REM ================================
REM START FRONTEND REACT (SPA)
REM ================================
echo [INFO] Lancement du frontend React (SPA)...

pushd %FRONTEND_DIR%
start "" /B serve dist -l %FRONTEND_PORT% --single
popd

REM ================================
REM OPEN BROWSER ON DASHBOARD
REM ================================
echo [INFO] Ouverture automatique du navigateur...
start "" "http://localhost:%FRONTEND_PORT%/dashboard"


REM ================================
REM FINAL
REM ================================
echo =========================================
echo   SYSTEME CANTINE LANCE AVEC SUCCES
echo =========================================
echo.

exit /b 0
