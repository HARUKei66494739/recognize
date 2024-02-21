@echo off
pushd "%~dp0"

echo start build > build.log

set r=0
if exist "bin\tee.exe" (
  echo existed tee.exe>> build.log 
) else (
  echo create tee.exe >> build.log
  echo �r���h�̏��񏀔����s���܂�
  C:\Windows\Microsoft.NET\Framework\v4.0.30319\csc /out:bin\tee.exe /target:exe /o+ src\tee\Program.cs 2>&1 >> build.log
  set r=%errorlevel%
  echo ok
  echo ""
)
if %r% neq 0 goto error

pushd src\py-recognition
powershell "Set-ExecutionPolicy -ExecutionPolicy Bypass -Scope Process ; .\build.ps1" 2>&1  | ..\..\bin\tee.exe --mask ..\..\build.log
set r=%errorlevel% 
popd
if %r% neq 0 goto error

call src\cs-recognition-frontend\build.bat 2>&1 | bin\tee.exe --mask build.log
if %errorlevel% neq 0 goto error
copy src\cs-recognition-frontend\recognize-gui.exe .\ 2>&1  | bin\tee.exe --mask build.log

echo build sucess >> build.log
echo ######################################################
echo #
echo # �r���h���������܂����I
echo #   recognize-gui.exe���N�����Ă�������
echo #
echo ######################################################

:end
pause
exit

:error
echo build error >> build.log
echo ######################################################
echo #
echo # �r���h�����s���܂���
echo #   build.log �Ƀr���h��񂪋L�ڂ���Ă���̂ł����
echo #   �A�g���������Ɖ������X���[�Y��������܂���
echo # �I�I�l��񂪋L�ڂ���Ă���\������܂��I�I
echo # �I�I�K�����O�ɂ��m�F���Ă��������I�I
echo #
echo ######################################################

pause