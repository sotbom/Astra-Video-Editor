param([string]$Python = "python", [switch]$DownloadFFmpeg)
$ErrorActionPreference = 'Stop'
Set-Location (Split-Path $PSScriptRoot -Parent)
if (-not (Test-Path '.venv/Scripts/python.exe')) {
    & $Python -m venv .venv
    if ($LASTEXITCODE -ne 0) { throw 'Python 3.12–3.14 is required.' }
}
& ./.venv/Scripts/python.exe -m pip install -r requirements-lock.txt
if ($LASTEXITCODE -ne 0) { throw 'Dependency installation failed.' }
if ($DownloadFFmpeg) {
    New-Item -ItemType Directory -Force tools | Out-Null
    $archive = Join-Path $PWD 'tools/ffmpeg-9.0.2-essentials.zip'
    Invoke-WebRequest 'https://www.gyan.dev/ffmpeg/builds/packages/ffmpeg-9.0.2-essentials_build.zip' -OutFile $archive
    $expected = '60F467265B1E312373DBCD92200C2618A74850F98D3D078E94296BB3FA2047BA'
    if ((Get-FileHash $archive -Algorithm SHA256).Hash -ne $expected) {
        throw 'FFmpeg checksum mismatch. Do not execute this archive.'
    }
    Expand-Archive -LiteralPath $archive -DestinationPath tools -Force
}
& ./.venv/Scripts/python.exe -m pip check
if ($LASTEXITCODE -ne 0) { throw 'Dependency consistency check failed.' }
& $PSScriptRoot/verify_ffmpeg.ps1
