$ErrorActionPreference = 'Stop'
$repoRoot = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
$audioDir = Join-Path $repoRoot 'tmp\submission-audio'
New-Item -ItemType Directory -Path $audioDir -Force | Out-Null
Add-Type -AssemblyName System.Speech
$synth = New-Object System.Speech.Synthesis.SpeechSynthesizer
$synth.Rate = 1
try {
  $scenes = Get-Content -LiteralPath (Join-Path $PSScriptRoot 'submission_script.json') -Raw | ConvertFrom-Json
  foreach ($scene in $scenes) {
    $synth.SetOutputToWaveFile((Join-Path $audioDir ($scene.id + '.wav')))
    $synth.Speak($scene.text)
    $synth.SetOutputToNull()
  }
} finally { $synth.Dispose() }
$python = Join-Path $repoRoot '.venv\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $python)) { $python = 'python' }
Push-Location -LiteralPath $repoRoot
try {
  & $python 'demo/tooling/submission_timing.py'
  if ($LASTEXITCODE -ne 0) { throw 'Could not prepare narration timing.' }
} finally { Pop-Location }
Write-Host 'Narration ready. Run node demo/tooling/record_submission.js from the repository root.'
