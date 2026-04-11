@echo off
REM Wasla AI Agent - Docker Setup Validation Script (Windows)
REM This script checks if your environment is ready for Docker deployment

echo.
echo 🔍 Wasla AI Agent - Docker Setup Validation
echo ==========================================
echo.

REM Check Docker
echo Checking Docker installation...
docker --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [X] Docker not found
    echo Please install Docker Desktop from https://www.docker.com/products/docker-desktop
    exit /b 1
)
echo [✓] Docker found

REM Check Docker Compose
echo Checking Docker Compose...
docker compose version >nul 2>&1
if %errorlevel% equ 0 (
    echo [✓] Docker Compose found
) else (
    docker-compose --version >nul 2>&1
    if %errorlevel% neq 0 (
        echo [X] Docker Compose not found
        echo Please install Docker Compose
        exit /b 1
    )
    echo [✓] Docker Compose found
)

REM Check if Docker daemon is running
echo Checking Docker daemon...
docker info >nul 2>&1
if %errorlevel% neq 0 (
    echo [X] Docker daemon not running
    echo Please start Docker Desktop
    exit /b 1
)
echo [✓] Docker daemon running

REM Check .env file
echo.
echo Checking configuration...

if not exist ".env" (
    echo [!] .env file not found
    echo Creating from .env.example...
    if exist ".env.example" (
        copy .env.example .env >nul
        echo [✓] Created .env from .env.example
        echo [!] Please edit .env and set your LLM_API_KEY
    ) else (
        echo [X] .env.example not found
        exit /b 1
    )
) else (
    echo [✓] .env file exists
)

REM Check if API key is set
echo Checking LLM_API_KEY...
findstr /C:"LLM_API_KEY=sk-" .env >nul 2>&1
if %errorlevel% equ 0 (
    echo [✓] API key is set
) else (
    findstr /C:"LLM_API_KEY=hf_" .env >nul 2>&1
    if %errorlevel% equ 0 (
        echo [✓] API key is set
    ) else (
        echo [!] API key not set or invalid
        echo Please edit .env and set LLM_API_KEY
        echo Get a free key from https://openrouter.ai (recommended) or https://hf.co/settings/tokens
    )
)

REM Check required files
echo.
echo Checking required files...

if exist "Dockerfile" (
    echo [✓] Dockerfile
) else (
    echo [X] Dockerfile not found
    exit /b 1
)

if exist "docker-compose.yml" (
    echo [✓] docker-compose.yml
) else (
    echo [X] docker-compose.yml not found
    exit /b 1
)

if exist "requirements.txt" (
    echo [✓] requirements.txt
) else (
    echo [X] requirements.txt not found
    exit /b 1
)

if exist "app\main.py" (
    echo [✓] app\main.py
) else (
    echo [X] app\main.py not found
    exit /b 1
)

REM Check docker-compose.yml syntax
echo.
echo Validating docker-compose.yml...
docker compose config >nul 2>&1
if %errorlevel% equ 0 (
    echo [✓] Valid
) else (
    echo [X] Invalid
    exit /b 1
)

REM Summary
echo.
echo ==========================================
echo [✓] All checks passed!
echo.
echo You're ready to deploy! Run:
echo.
echo   docker-compose up -d
echo.
echo Then access the API at http://localhost:8000/docs
echo.
echo For more information, see:
echo   - QUICKSTART.md - Get running in 5 minutes
echo   - DOCKER_SETUP.md - Full deployment guide
echo.
