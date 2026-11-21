$ErrorActionPreference = 'Stop'
Set-Location (Split-Path $PSScriptRoot -Parent)
& ./.venv/Scripts/python.exe -c "from app.utils.paths import find_tool; import subprocess; [subprocess.run([find_tool(n), '-version'], check=True) for n in ('ffmpeg', 'ffprobe')]"
if ($LASTEXITCODE -ne 0) { throw 'FFmpeg verification failed.' }
