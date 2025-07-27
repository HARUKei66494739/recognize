
@echo off
pushd "%~dp0"

set PIPENV_VENV_IN_PROJECT=1

python -m pipenv install --dev
if %errorlevel% neq 0 goto error

python -m pipenv requirements > requirements.txt
echo pyinstaller==6.13.0 >> requirements.txt
echo pyinstaller-hooks-contrib==2025.3 >> requirements.txt

popd
exit /b 0

error:
popd
pause
