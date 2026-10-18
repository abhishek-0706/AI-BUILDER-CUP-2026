# Free local voice tools only; no API keys, cloud calls, or uploads.
# Requires existing uv and curl; downloads official public artifacts.
[CmdletBinding()]
param()
$ErrorActionPreference = 'Stop'
$repoRoot = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
$voiceRoot = Join-Path $repoRoot 'tmp/voice-tools'
$pythonExe = Join-Path $voiceRoot 'venv/Scripts/python.exe'
$sourceRevision = '74a1d147b17a8c3092dd5430504bd83ef6c7eb23'
$modelRevision = 'f36e7edfe1684461a8343844af60babc2efbb727'
$weightHash = '9652c27e92b6b2a91632590ac9962ef7ae2b712e5c5b7f4c34ec55ee2b37ab9e'
$uvExe = (Get-Command uv.exe -ErrorAction Stop).Source
$curlExe = (Get-Command curl.exe -ErrorAction Stop).Source
$envNames = @('UV_CACHE_DIR', 'UV_PYTHON_INSTALL_DIR', 'UV_PYTHON_BIN_DIR')
$savedEnv = @{}
foreach ($name in $envNames) { $savedEnv[$name] = [Environment]::GetEnvironmentVariable($name, 'Process') }
function Get-VoiceArtifact([string]$Uri, [string]$Destination, [string]$ExpectedHash = '') {
  if ((Test-Path -LiteralPath $Destination) -and $ExpectedHash) {
    if ((Get-FileHash -LiteralPath $Destination -Algorithm SHA256).Hash.ToLowerInvariant() -eq $ExpectedHash) { return }
  }
  $partPath = $Destination + '.part'
  & $curlExe --fail --location --retry 3 --retry-all-errors --silent --show-error $Uri --output $partPath
  if ($LASTEXITCODE -ne 0) { throw 'An official voice artifact could not be downloaded.' }
  if ($ExpectedHash -and (Get-FileHash -LiteralPath $partPath -Algorithm SHA256).Hash.ToLowerInvariant() -ne $ExpectedHash) {
    throw 'Official voice checkpoint SHA256 mismatch. It will not be loaded.'
  }
  Move-Item -LiteralPath $partPath -Destination $Destination -Force
}
try {
  New-Item -ItemType Directory -Path $voiceRoot -Force | Out-Null
  $env:UV_CACHE_DIR = Join-Path $voiceRoot 'uv-cache'
  $env:UV_PYTHON_INSTALL_DIR = Join-Path $voiceRoot 'python'
  $env:UV_PYTHON_BIN_DIR = Join-Path $voiceRoot 'bin'
  & $uvExe python install 3.11.15 --no-bin
  if ($LASTEXITCODE -ne 0) { throw 'Isolated Python installation failed.' }
  if (-not (Test-Path -LiteralPath $pythonExe)) {
    & $uvExe venv --python 3.11.15 (Join-Path $voiceRoot 'venv')
    if ($LASTEXITCODE -ne 0) { throw 'Isolated voice environment could not be created.' }
  }
  & $uvExe pip install --python $pythonExe --index 'https://download.pytorch.org/whl/cpu' --index-strategy unsafe-best-match -r (Join-Path $PSScriptRoot 'requirements-voice.txt')
  if ($LASTEXITCODE -ne 0) { throw 'Isolated CPU audio dependencies could not be installed.' }
  $sourceRoot = Join-Path $voiceRoot 'OpenVoice'
  $packageRoot = Join-Path $sourceRoot 'openvoice'
  $converterRoot = Join-Path $voiceRoot 'converter'
  New-Item -ItemType Directory -Path $packageRoot, $converterRoot -Force | Out-Null
  foreach ($fileName in @('models.py', 'modules.py', 'attentions.py', 'commons.py', 'transforms.py')) {
    Get-VoiceArtifact ('https://raw.githubusercontent.com/myshell-ai/OpenVoice/' + $sourceRevision + '/openvoice/' + $fileName) (Join-Path $packageRoot $fileName)
  }
  [System.IO.File]::WriteAllText((Join-Path $packageRoot '__init__.py'), '')
  Get-VoiceArtifact ('https://raw.githubusercontent.com/myshell-ai/OpenVoice/' + $sourceRevision + '/LICENSE') (Join-Path $sourceRoot 'LICENSE')
  Get-VoiceArtifact ('https://huggingface.co/myshell-ai/OpenVoiceV2/resolve/' + $modelRevision + '/converter/config.json') (Join-Path $converterRoot 'config.json')
  Get-VoiceArtifact ('https://huggingface.co/myshell-ai/OpenVoiceV2/resolve/' + $modelRevision + '/converter/checkpoint.pth') (Join-Path $converterRoot 'checkpoint.pth') $weightHash
  $manifest = @{source_revision=$sourceRevision; model_revision=$modelRevision; checkpoint_sha256=$weightHash; checkpoint_bytes=(Get-Item -LiteralPath (Join-Path $converterRoot 'checkpoint.pth')).Length}
  [System.IO.File]::WriteAllText((Join-Path $voiceRoot 'model-manifest.json'), ($manifest | ConvertTo-Json), [System.Text.UTF8Encoding]::new($false))
  & $pythonExe -c "import torch, numpy, soundfile; print('Offline CPU voice tools ready:', torch.__version__, numpy.__version__, soundfile.__version__)"
  if ($LASTEXITCODE -ne 0) { throw 'Offline voice dependency import check failed.' }
} finally {
  foreach ($name in $envNames) { [Environment]::SetEnvironmentVariable($name, $savedEnv[$name], 'Process') }
}
Write-Output 'Ready. Use clone_narration.py with a local --sample. Voice files stay in ignored tmp.'
