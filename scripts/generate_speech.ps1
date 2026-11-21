$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path $PSScriptRoot -Parent
$fixtureDir = Join-Path $projectRoot 'tests/fixtures/generated'
New-Item -ItemType Directory -Force -Path $fixtureDir | Out-Null
$speechPath = Join-Path $fixtureDir 'speech.wav'
$speechVoice = New-Object -ComObject SAPI.SpVoice
$speechStream = New-Object -ComObject SAPI.SpFileStream
try {
    $speechStream.Open($speechPath, 3, $false)
    $speechVoice.AudioOutputStream = $speechStream
    $speechVoice.Rate = -1
    $speechVoice.Speak('Welcome to Astra Video Editor. This is a test of offline speech recognition. We can edit subtitles and export a video without sending audio to the cloud.') | Out-Null
} finally {
    $speechStream.Close()
}
Write-Output $speechPath
