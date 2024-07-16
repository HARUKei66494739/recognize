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
	echo torch���g�p�����r���h���܂�
	Get-Content .\requirements.txt | foreach { $_ -replace "^(torch|mkl|faster-whisper|accelerate|transformers).*$", "" } | Set-Content .\requirements-without_torch.txt
	$REQUIREMENTS_FILE = "requirements-without_torch.txt"
}

# �v���O���X�o�[������
$global:progressPreference = 'silentlyContinue'


echo python�̃C���X�g�[���m�F
Get-Command pip3 > $null
if (-not($?)) {
    echo pip��������Ȃ��̂�python�̃C���X�g�[�����s���܂�
    winget install python3.11 --silent
    if($LASTEXITCODE -ne 0) {
        echo �C���X�g�[�������s�܂��̓L�����Z������܂���
        exit 1
    }
    echo python���C���X�g�[������܂����B��x���Ă�����x�r���h���Ă�������
    exit 1
}
echo ok
echo ""

echo python�̃o�[�W�����m�F
$py_v = python -V | ConvertFrom-String -Delimiter '[\s\.]+'
# python 3.10.x�ȏ��v��
if(($py_v.P2 -ne 3) -or (($py_v.P2 -eq 3) -and ($py_v.P3 -lt 10))) {
    echo �G���[
    echo �C���X�g�[������Ă���python�̓T�|�[�g����Ă��܂���
    python -V
    Get-Command python | Select-Object Source | Format-Table -AutoSize -Wrap
    exit 1
}
echo ok
echo ""


#echo git�̃C���X�g�[���m�F
#Get-Command git > $null
#if(-not($?)) {
#    echo git��������Ȃ��̂�git�̃C���X�g�[�����s���܂�
#    winget install git.git
#    if($LASTEXITCODE -ne 0) {
#        echo �C���X�g�[�������s�܂��̓L�����Z������܂���
#        exit 1
#    }
#}
#echo ok
#echo ""

echo ��ƃf�B���N�g���̏������s���܂�
If (Test-Path .\.build) {
    echo �Â���ƃf�B���N�g�����폜���܂�
    Remove-Item -path .\.build -recurse
    if($LASTEXITCODE -ne 0) {
        echo �Â���ƃf�B���N�g���̍폜�Ɏ��s���܂���
        exit 1
    }
    echo ok
    echo ""
}

mkdir .build
if($LASTEXITCODE -ne 0) {
    echo ��ƃf�B���N�g���̍쐬�Ɏ��s���܂���
    exit 1
}
Copy-Item -Path .\src -Destination .\.build.\src -Recurse
if($LASTEXITCODE -ne 0) {
    echo �\�[�X�R�[�h�̕����Ɏ��s���܂���
    exit 1
}
Copy-Item -Path .\Pipfile.build -Destination .\.build.\Pipfile
if($LASTEXITCODE -ne 0) {
    echo Pipfile�̕����Ɏ��s���܂���
    exit 1
}


pushd .build


$env:PIPENV_VENV_IN_PROJECT = 1
#$env:Path = [System.Environment]::GetEnvironmentVariable("Path","Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path","User")

echo python����pipenv���C���X�g�[�����܂�
pip3 install pipenv
if($LASTEXITCODE -ne 0) {
    echo �C���X�g�[���Ɏ��s���܂���
    popd
    exit 1
}
echo ok
echo ""

echo ���z�����쐬��python�ˑ��֌W�𕜌����܂�
python -m pipenv install --dev --skip-lock
if($LASTEXITCODE -ne 0) {
    echo python�ˑ��֌W�̕����Ɏ��s���܂���
    popd
    exit 1
}

python -m pipenv shell pip install webrtcvad
if($LASTEXITCODE -ne 0) {
    echo �C���X�g�[���Ɏ��s���܂���
    echo C++�r���h�����C���X�g�[�����܂�
    winget install Microsoft.VisualStudio.2022.BuildTools --silent --override "--wait --quiet --add Microsoft.VisualStudio.Workload.VCTools --includeRecommended"
    if($LASTEXITCODE -ne 0) {
        echo �C���X�g�[�������s�܂��̓L�����Z������܂���
        popd
        exit 1
    }
}
echo ok
echo ""

python -m pipenv shell pip install -r ../$REQUIREMENTS_FILE --no-cache-dir
if($LASTEXITCODE -ne 0) {
    echo python�ˑ��֌W�̕����Ɏ��s���܂���
    popd
    exit 1
}

# CUDA�֘A���e�ʂ���������̂ŃL���b�V���͍폜����
# python -m pipenv shell pip cache purge
echo ok
echo ""


echo �u�[�g���[�_�[�������ւ��܂�
# NTFS��փX�g���[���������Ă���_�E�����[�h�����폜����(�G���[�͖���)
(Get-ChildItem -Path ..\bootloader\bootloader.zip -File).FullName | ForEach-Object { Remove-Item -Path $_ -Stream Zone.Identifier } 2>&1 > $null
#���O�Ɍ��m�������
#if (ExistsStream ..\bootloader\bootloader.zip Zone.Identifier) {
#  Remove-Item -Path ..\bootloader\bootloader.zip -Stream Zone.Identifier
#}
Expand-Archive -Path ..\bootloader\bootloader.zip -DestinationPath .\.venv\Lib\site-packages\PyInstaller\bootloader\Windows-64bit-intel -Force
if($LASTEXITCODE -ne 0) {
    echo �u�[�g���[�_�[�������ւ��Ɏ��s���܂���
    popd
    exit 1
}
echo ok
echo ""

echo exe�������s���܂�
python -m pipenv run archive1
if($LASTEXITCODE -ne 0) {
    echo exe���Ɏ��s���܂���
    popd
    exit 1
}
$cd = Get-Location
echo "$cd\dist\recognize �ɍ쐬���܂���"
echo ok
echo ""

echo ���z�����폜���܂�
python -m pipenv --rm
if($LASTEXITCODE -ne 0) {
    echo �폜�Ɏ��s���܂���
    popd
    exit 1
}
echo ok
echo ""


popd


echo �A�[�J�C�u���ړ����܂�
If (Test-Path .\dist) {
    echo �����̃A�[�J�C�u���폜���܂�
    Remove-Item -path .\dist -recurse
    if($LASTEXITCODE -ne 0) {
        echo �����̃A�[�J�C�u�̍폜�Ɏ��s���܂���
        exit 1
    }
}
move .build\dist .
if($LASTEXITCODE -ne 0) {
    echo �A�[�J�C�u�̈ړ��Ɏ��s���܂���
    exit 1
}

echo ��ƃf�B���N�g�����폜���܂�
Remove-Item  -path .build -recurse
if($LASTEXITCODE -ne 0) {
    echo ��ƃf�B���N�g���̍폜�Ɏ��s���܂���
    exit 1
}

echo ����ɏI�����܂���
echo ""

$cd = Get-Location
echo ""
echo "�r���h���ꂽexe�̏ꏊ�F"
echo "$cd\dist\recognize"
exit 0