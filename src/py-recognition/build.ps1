function ExistsStream ($file, $stream) {
  foreach ($s in (Get-Item -Path $file -Stream *).Stream) {
    if ($s -eq $stream ) {
        return $true
    }
  }
  return $false
}

if(-not($env:RECOGNIZE_WITHOUT_TORCH)) {
	$REQUIREMENTS_FILE = "requirements.txt"
} else {
	echo torchを使用せずビルドします
	Get-Content .\requirements.txt | foreach { $_ -replace "^(torch|mkl|faster-whisper|accelerate|transformers).*$", "" } | Set-Content .\requirements-without_torch.txt
	$REQUIREMENTS_FILE = "requirements-without_torch.txt"
}

# プログレスバー無効化
$global:progressPreference = 'silentlyContinue'


echo 作業ディレクトリの準備を行います
If (Test-Path .\.build) {
    echo 古い作業ディレクトリを削除します
    Remove-Item -path .\.build -recurse
    if( -not $? ) {
        echo 古い作業ディレクトリの削除に失敗しました
        exit 1
    }
    echo ok
    echo ""
}

mkdir .build
if( -not $? ) {
    echo 作業ディレクトリの作成に失敗しました
    exit 1
}
Copy-Item -Path .\src -Destination .\.build\src -Recurse
if( -not $? ) {
    echo ソースコードの複製に失敗しました
    exit 1
}


pushd .build

echo python仮想環境を作成します
python -m venv .venv
if($LASTEXITCODE -ne 0) {
    echo 仮想環境の作成に失敗しました
    popd
    exit 1
}
.venv\Scripts\activate.ps1
echo ok
echo ""


echo python依存関係を復元します
pip install -r ../$REQUIREMENTS_FILE --no-cache-dir
if($LASTEXITCODE -ne 0) {
    echo python依存関係の復元に失敗しました
    popd
    exit 1
}
# CUDA関連が容量を圧迫するのでキャッシュは削除する
# pip cache purge
echo ok
echo ""

echo ブートローダーを差し替えます
# NTFS代替ストリームが持っているダウンロード情報を削除する(エラーは無視)
(Get-ChildItem -Path ..\bootloader\bootloader.zip -File).FullName | ForEach-Object { Remove-Item -Path $_ -Stream Zone.Identifier } 2>&1 > $null
#事前に検知する実装
#if (ExistsStream ..\bootloader\bootloader.zip Zone.Identifier) {
#  Remove-Item -Path ..\bootloader\bootloader.zip -Stream Zone.Identifier
#}
Expand-Archive -Path ..\bootloader\bootloader.zip -DestinationPath .\.venv\Lib\site-packages\PyInstaller\bootloader\Windows-64bit-intel -Force
if( -not $? ) {
    echo ブートローダーを差し替えに失敗しました
    popd
    exit 1
}
echo ok
echo ""

echo exe化を実行します
pyinstaller -n recognize --noconfirm `
  --additional-hooks-dir src\__pyinstaller `
  src\__main__.py
if($LASTEXITCODE -ne 0) {
    echo exe化に失敗しました
    popd
    exit 1
}
$cd = Get-Location
echo "$cd\dist\recognize に作成しました"
echo ok
echo ""

echo 仮想環境を終了します
deactivate
if($LASTEXITCODE -ne 0) {
    echo 仮想環境の終了に失敗しました
    popd
    exit 1
}
echo ok
echo ""


popd


echo アーカイブを移動します
If (Test-Path .\dist) {
    echo 既存のアーカイブを削除します
    Remove-Item -path .\dist -recurse
    if( -not $? ) {
        echo 既存のアーカイブの削除に失敗しました
        exit 1
    }
}
move .build\dist .
if( -not $? ) {
    echo アーカイブの移動に失敗しました
    exit 1
}

echo 作業ディレクトリを削除します
Remove-Item  -path .build -recurse
if( -not $? ) {
    echo 作業ディレクトリの削除に失敗しました
    exit 1
}

echo 正常に終了しました
echo ""

$cd = Get-Location
echo ""
echo "ビルドされたexeの場所："
echo "$cd\dist\recognize"
exit 0
