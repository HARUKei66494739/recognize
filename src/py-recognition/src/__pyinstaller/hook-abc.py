from PyInstaller.utils.hooks import collect_dynamic_libs, collect_data_files

hiddenimports = [
    "whisper",
    "faster_whisper",
    "transformers",
    "torch",
    "tensorflow",
    "tensorflow_hub",
#    "moonshine_voice",
    "charset_normalizer",
]


datas = []
datas += collect_data_files("src.resources")
datas += collect_data_files("silero_vad")


binaries = []
binaries += collect_dynamic_libs("openvr")
binaries += collect_dynamic_libs("moonshine_voice")
binaries += collect_dynamic_libs("src", destdir="./")
# --add-binary "./.venv/Lib/site-packages/openvr/*.dll;./openvr"