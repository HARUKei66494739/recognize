@echo off
PATH=%PATH%;C:\Program Files\dotnet
pushd "%~dp0"

pushd Sakura
dotnet clean -c Release
set r=%errorlevel%
if %r% neq 0 goto error

dotnet build -c Release
set r=%errorlevel%
if %r% neq 0 goto error

dotnet publish -c Release
set r=%errorlevel%
if %r% neq 0 goto error
popd

:error
exit /B %r%