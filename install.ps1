# install.ps1

Write-Host "Checking and installing requirements..." -ForegroundColor Cyan

# Check Python version
$pythonVersion = (python --version 2>&1)
if ($LASTEXITCODE -ne 0 -or [version]($pythonVersion -replace 'Python ') -lt [version]"3.10.0") {
    Write-Host "Python 3.10+ not found. Installing..." -ForegroundColor Yellow
    winget install Python.Python.3.10
    if ($LASTEXITCODE -ne 0) {
        Write-Host "Failed to install Python. Please install manually." -ForegroundColor Red
        exit 1
    }
}

# Check and install FFmpeg
Write-Host "Checking for ffmpeg..." -ForegroundColor Yellow
$ffmpeg = Get-Command ffmpeg -ErrorAction SilentlyContinue
if (-not $ffmpeg) {
    Write-Host "Installing FFmpeg..." -ForegroundColor Yellow
    winget install ffmpeg
    Write-Host "FFmpeg installed. Please restart your system." -ForegroundColor Green
    exit 0
}

# Check and create venv
if (-not (Test-Path "venv")) {
    Write-Host "Creating virtual environment..." -ForegroundColor Yellow
    python -m venv venv
}



# Check and install required packages
Write-Host "Checking Python packages..." -ForegroundColor Yellow
$requirements = Get-Content requirements.txt
$installed = pip freeze
$missing = @()

foreach ($req in $requirements) {
    if ($req -match '^[^#]') {  # Skip comments
        $package = ($req -split '==|>=')[0]
        if ($installed -notcontains $req) {
            $missing += $req
        }
    }
}

if ($missing.Count -gt 0) {
    Write-Host "Installing missing packages..." -ForegroundColor Yellow
    foreach ($pkg in $missing) {
        pip install $pkg
    }
}

Write-Host "All requirements are satisfied!" -ForegroundColor Green

Write-Host "Activating virtual environment..." -ForegroundColor Yellow
.\venv\Scripts\Activate.ps1