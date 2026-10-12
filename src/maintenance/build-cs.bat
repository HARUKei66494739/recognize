@rem 
@rem  CI用C# exeビルドバッチ
@rem 

@echo off
pushd "%~dp0"

echo -------------------------------
echo Build recognition GUI
echo -------------------------------
pushd ..\cs-recognition-frontend
call build.bat
set r=%errorlevel%
if %r% neq 0 goto error
popd

echo -------------------------------
echo Build illuminate
echo -------------------------------
pushd ..\cs-illuminate
call build.bat
set r=%errorlevel%
if %r% neq 0 goto error
popd

echo -------------------------------
echo Build sakura
echo -------------------------------
pushd ..\cs-sakura
call build.bat
set r=%errorlevel%
if %r% neq 0 goto error
popd

echo -------------------------------
echo end Build
echo -------------------------------

:error
exit /B %r%


