from PyInstaller.utils.hooks import collect_dynamic_libs



binaries = []
binaries += collect_dynamic_libs("openvr")
binaries += collect_dynamic_libs("src", destdir="./")
# --add-binary "./.venv/Lib/site-packages/openvr/*.dll;./openvr"