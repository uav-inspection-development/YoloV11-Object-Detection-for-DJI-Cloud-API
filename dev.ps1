# PowerShell script for development tasks
param(
    [Parameter(Position=0)]
    [string]$Command = "help"
)

function Show-Help {
    Write-Host "Available commands:" -ForegroundColor Green
    Write-Host "  install      Install production dependencies" -ForegroundColor Yellow
    Write-Host "  install-dev  Install development dependencies" -ForegroundColor Yellow
    Write-Host "  lint         Run flake8 linting" -ForegroundColor Yellow
    Write-Host "  type-check   Run mypy type checking" -ForegroundColor Yellow
    Write-Host "  test         Run pytest tests" -ForegroundColor Yellow
    Write-Host "  format       Format code with black and isort" -ForegroundColor Yellow
    Write-Host "  check        Run all checks (lint + type-check + test)" -ForegroundColor Yellow
    Write-Host "  clean        Clean up cache files" -ForegroundColor Yellow
}

function Install-Dependencies {
    pip install -r requirements.txt
}

function Install-DevDependencies {
    pip install -r requirements.txt
    pip install -r requirements-dev.txt
}

function Run-Lint {
    Write-Host "Running flake8 linting..." -ForegroundColor Blue
    flake8 src
}

function Run-TypeCheck {
    Write-Host "Running mypy type checking..." -ForegroundColor Blue
    mypy src
}

function Run-Tests {
    Write-Host "Running pytest tests..." -ForegroundColor Blue
    pytest tests/ --cov=src --cov-report=term-missing
}

function Format-Code {
    Write-Host "Formatting code with black and isort..." -ForegroundColor Blue
    black src tests
    isort src tests
}

function Run-AllChecks {
    Write-Host "Running all checks..." -ForegroundColor Blue
    Run-Lint
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
    
    Run-TypeCheck
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
    
    Run-Tests
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
    
    Write-Host "All checks passed!" -ForegroundColor Green
}

function Clean-Cache {
    Write-Host "Cleaning cache files..." -ForegroundColor Blue
    Get-ChildItem -Path . -Recurse -Directory -Name "__pycache__" | Remove-Item -Recurse -Force
    Get-ChildItem -Path . -Recurse -Directory -Name ".pytest_cache" | Remove-Item -Recurse -Force
    Get-ChildItem -Path . -Recurse -Directory -Name ".mypy_cache" | Remove-Item -Recurse -Force
    Get-ChildItem -Path . -Recurse -File -Name "*.pyc" | Remove-Item -Force
    Get-ChildItem -Path . -Recurse -File -Name "*.pyo" | Remove-Item -Force
    Get-ChildItem -Path . -Recurse -File -Name "*.pyd" | Remove-Item -Force
    Get-ChildItem -Path . -Recurse -File -Name ".coverage" | Remove-Item -Force
    Get-ChildItem -Path . -Recurse -File -Name "*.cover" | Remove-Item -Force
}

switch ($Command.ToLower()) {
    "help" { Show-Help }
    "install" { Install-Dependencies }
    "install-dev" { Install-DevDependencies }
    "lint" { Run-Lint }
    "type-check" { Run-TypeCheck }
    "test" { Run-Tests }
    "format" { Format-Code }
    "check" { Run-AllChecks }
    "clean" { Clean-Cache }
    default { 
        Write-Host "Unknown command: $Command" -ForegroundColor Red
        Show-Help 
    }
}
