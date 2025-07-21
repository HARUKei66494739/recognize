@echo off
pushd "%~dp0"

echo ############## recognize ���r���h���܂� ##############
pushd src\py-recognition
powershell "Set-ExecutionPolicy -ExecutionPolicy Bypass -Scope Process ; .\build.ps1"
if %errorlevel% neq 0 goto error
popd

echo ############ recognize-gui ���r���h���܂� ############
call src\cs-recognition-frontend\build.bat
if %errorlevel% neq 0 goto error
copy src\cs-recognition-frontend\dist\recognize-gui.exe 
if %errorlevel% neq 0 goto error


echo ############# illuminate ���r���h���܂� ##############
call src\cs-illuminate\build.bat 
if %errorlevel% neq 0 goto error

echo ######################################################
echo #
echo # �r���h���������܂����I
echo #   recognize-gui.exe���N�����Ă�������
echo #
echo ######################################################

:end
pause
exit /B

:error
echo ######################################################
echo #
echo # �r���h�����s���܂���
echo #
echo ######################################################

pause
exit /B 1