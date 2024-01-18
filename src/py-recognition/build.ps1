echo python�̃C���X�g�[���m�F
Get-Command pip3 > $null
if (-not($?)) {
    echo pip��������Ȃ��̂�python�̃C���X�g�[�����s���܂�
    winget install python3.10
    if($LASTEXITCODE -ne 0) {
        echo �C���X�g�[�������s�܂��̓L�����Z������܂���
        exit 1
    }
}
echo ok

echo git�̃C���X�g�[���m�F
Get-Command git > $null
if(-not($?)) {
    echo git��������Ȃ��̂�git�̃C���X�g�[�����s���܂�
    winget install git.git
    if($LASTEXITCODE -ne 0) {
        echo �C���X�g�[�������s�܂��̓L�����Z������܂���
        exit 1
    }
}
echo ok

$env:Path = [System.Environment]::GetEnvironmentVariable("Path","Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path","User")

echo python����pipenv���C���X�g�[�����܂�
pip3 install pipenv
if($LASTEXITCODE -ne 0) {
    echo �C���X�g�[���Ɏ��s���܂���
    exit 1
}
echo ok

echo ���z�����쐬��python�ˑ��֌W�𕜌����܂�
python -m pipenv install
if($LASTEXITCODE -ne 0) {
    echo python�ˑ��֌W�̕����Ɏ��s���܂���
    exit 1
}
python -m pipenv install --dev
if($LASTEXITCODE -ne 0) {
    echo python�ˑ��֌W�̕����Ɏ��s���܂���
    exit 1
}
echo ok

echo exe�������s���܂�
python -m pipenv run archive1
if($LASTEXITCODE -ne 0) {
    echo exe���Ɏ��s���܂���
    exit 1
}
$cd = Get-Location
echo "$cd\dist\recognize �ɍ쐬���܂���"
echo ok

echo ���z�����폜���܂�
python -m pipenv --rm
if($LASTEXITCODE -ne 0) {
    echo �폜�Ɏ��s���܂���
    exit 1
}
echo ok

echo ����ɏI�����܂���

echo ""
echo "�r���h���ꂽexe�̏ꏊ�F"
echo "$cd\dist\recognize"
exit 0