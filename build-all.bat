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
(powershell "Set-ExecutionPolicy -ExecutionPolicy Bypass -Scope Process ; .\build.ps1" 2>&1 & call echo %%^^errorlevel%% ^> ..\..\build.dat)  | ..\..\bin\tee.exe --mask ..\..\build.log
popd
(
    set /P r=
)< build.dat
if %r% neq 0 goto error

(call src\cs-illuminate\build.bat 2>&1 & call echo %%^^errorlevel%% ^> build.dat) | bin\tee.exe --mask build.log
popd
(
    set /P r=
)< build.dat
(call src\cs-recognition-frontend\build.bat 2>&1 & call echo %%^^errorlevel%% ^> build.dat) | bin\tee.exe --mask build.log
popd
(
    set /P r=
)< build.dat
if %r% neq 0 goto error
(copy src\cs-recognition-frontend\bin\Release\net8.0-windows\win-x64\publish\recognize-gui.exe .\ 2>&1 & call echo %%^^errorlevel%% ^> build.dat) | bin\tee.exe --mask build.log
popd
(
    set /P r=
)< build.dat
if %r% neq 0 goto error

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