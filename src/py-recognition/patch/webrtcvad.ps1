pushd $PSScriptRoot

pushd ../.venv/Lib/site-packages/
Get-Content -Encoding UTF8 webrtcvad.py `
  | ForEach-Object {$_ -replace "import pkg_resources", "import harukei_pkg_resources as pkg_resources"}`
  | Out-File -Encoding UTF8 webrtcvad.py.2 -NoClobber
Move-Item ./webrtcvad.py.2 -Destination ./webrtcvad.py -Force
popd

Copy-Item ./harukei_pkg_resources.py -Destination ../.venv/Lib/site-packages -Force
popd

echo done.