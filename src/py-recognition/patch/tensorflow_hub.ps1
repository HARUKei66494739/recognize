pushd $PSScriptRoot

pushd ../.venv/Lib/site-packages/tensorflow_hub/
Get-Content -Encoding UTF8 __init__.py `
  | ForEach-Object {$_ -replace "from pkg_resources import", "from .harukei_pkg_resources import"}`
  | Out-File -Encoding UTF8 __init__.py.2 -NoClobber
Move-Item ./__init__.py.2 -Destination ./__init__.py -Force
popd

Copy-Item ./harukei_pkg_resources.py -Destination ../.venv/Lib/site-packages/tensorflow_hub -Force
popd

echo done.