param()
$ErrorActionPreference = 'Stop'
$repo = Split-Path $PSScriptRoot -Parent
Set-Location -LiteralPath $repo
$savedBuildPath = $env:PATH
$env:PATH = "$repo/.venv/Scripts;$env:SystemRoot/System32;$env:SystemRoot"
try {
& .venv/Scripts/python.exe -m PyInstaller --clean --noconfirm --onedir --windowed --name AstraVideoEditor --paths . --distpath artifacts/portable --workpath artifacts/build --specpath packaging packaging/entry.py
if ($LASTEXITCODE -ne 0) { throw 'PyInstaller build failed' }
} finally { $env:PATH = $savedBuildPath }
$analysis = Get-Content -Raw 'artifacts/build/AstraVideoEditor/Analysis-00.toc'
if ($analysis -match 'CodexPrimaryRuntime|native\\\\poppler') {
    throw 'Dependency contamination detected; do not distribute this build.'
}
$bundle = Join-Path $repo 'artifacts/portable/AstraVideoEditor'
New-Item -ItemType Directory -Force "$bundle/_internal/tools/bin" | Out-Null
Copy-Item -LiteralPath 'tools/ffmpeg-9.0.2-essentials_build/bin/ffmpeg.exe','tools/ffmpeg-9.0.2-essentials_build/bin/ffprobe.exe' -Destination "$bundle/_internal/tools/bin"
Copy-Item -LiteralPath 'docs/LICENSES.md','LICENSE' -Destination $bundle
Copy-Item -LiteralPath 'tools/ffmpeg-9.0.2-essentials_build/LICENSE' -Destination "$bundle/FFmpeg-LICENSE.txt"
$manifest = Get-ChildItem -LiteralPath $bundle -Recurse -File | ForEach-Object {
    [PSCustomObject]@{ path = [IO.Path]::GetRelativePath($bundle, $_.FullName); bytes = $_.Length; sha256 = (Get-FileHash -LiteralPath $_.FullName -Algorithm SHA256).Hash }
}
$manifest | ConvertTo-Json -Depth 3 | Set-Content -Encoding utf8 "$bundle/manifest.json"
Compress-Archive -Path "$bundle/*" -DestinationPath 'artifacts/AstraVideoEditor-portable-candidate.zip' -Force
Get-FileHash 'artifacts/AstraVideoEditor-portable-candidate.zip' -Algorithm SHA256 | Format-List | Out-File artifacts/portable-checksum.txt
