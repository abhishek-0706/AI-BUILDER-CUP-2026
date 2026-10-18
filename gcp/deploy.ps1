param(
  [Parameter(Mandatory=$true)][string]$ProjectId,
  [ValidatePattern('^[^@\s]+@[^@\s]+\.[^@\s]+$')][string]$Account = 'company-account@example.com',
  [ValidateSet('all','service','schema','seed','forecast','evaluate','infrastructure')][string]$Mode = 'all',
  [switch]$PublicDemo,
  [string]$TokenFile
)
$ErrorActionPreference = 'Stop'
$repoRoot = Split-Path -Parent $PSScriptRoot
$portableRoot = Join-Path $repoRoot 'tmp\cloud-tools\google-cloud-sdk'
$portableBin = Join-Path $portableRoot 'bin'
$bashCommand = Get-Command bash -ErrorAction SilentlyContinue
$gitBash = Join-Path $env:ProgramFiles 'Git\bin\bash.exe'
if ($bashCommand) { $bashCli = $bashCommand.Source }
elseif (Test-Path -LiteralPath $gitBash) { $bashCli = $gitBash }
else { throw 'Install Git for Windows to provide Bash, or run deploy.sh in Cloud Shell.' }
$names = @('GCP_PROJECT','PATH','PYTHON_BIN','CLOUDSDK_PYTHON','CLOUDSDK_BQ_PYTHON','CLOUDSDK_CORE_ACCOUNT','PUBLIC_DEMO','APP_KEY_FILE')
$previous = @{}
foreach ($name in $names) { $previous[$name] = [Environment]::GetEnvironmentVariable($name,'Process') }
try {
  $env:GCP_PROJECT = $ProjectId
  $env:CLOUDSDK_CORE_ACCOUNT = $Account
  if (Test-Path -LiteralPath $portableBin) { $env:PATH = $portableBin + ';' + $env:PATH }
  $bundledPython = Join-Path $portableRoot 'platform\bundledpython\python.exe'
  $localPython = Join-Path $repoRoot '.venv\Scripts\python.exe'
  if (Test-Path -LiteralPath $bundledPython) {
    $env:CLOUDSDK_PYTHON = $bundledPython.Replace('\','/')
    $env:CLOUDSDK_BQ_PYTHON = $env:CLOUDSDK_PYTHON
  }
  if (Test-Path -LiteralPath $localPython) { $env:PYTHON_BIN = $localPython.Replace('\','/') }
  elseif (Test-Path -LiteralPath $bundledPython) { $env:PYTHON_BIN = $env:CLOUDSDK_PYTHON }
  else { throw 'Create .venv with a supported Python, or install the Cloud CLI with bundled Python first.' }
  $env:PUBLIC_DEMO = if ($PublicDemo) { 'true' } else { 'false' }
  $env:APP_KEY_FILE = ''
  if ($PublicDemo) {
    if (-not $TokenFile) { throw 'Supply -TokenFile for the explicitly authenticated public demo.' }
    $tokenPath = (Resolve-Path -LiteralPath $TokenFile).Path
    $tmpRoot = [IO.Path]::GetFullPath((Join-Path $repoRoot 'tmp')) + [IO.Path]::DirectorySeparatorChar
    if ($tokenPath.StartsWith($repoRoot + [IO.Path]::DirectorySeparatorChar,[StringComparison]::OrdinalIgnoreCase) -and -not $tokenPath.StartsWith($tmpRoot,[StringComparison]::OrdinalIgnoreCase)) {
      throw 'Keep the token file outside this repository or inside ignored tmp/.'
    }
    $env:APP_KEY_FILE = $tokenPath.Replace('\','/')
  }
  Push-Location -LiteralPath $repoRoot
  try {
    & $bashCli 'gcp/deploy.sh' $Mode
    if ($LASTEXITCODE -ne 0) { throw ('Deployment stopped with exit code ' + $LASTEXITCODE) }
  } finally { Pop-Location }
} finally {
  foreach ($name in $names) { [Environment]::SetEnvironmentVariable($name,$previous[$name],'Process') }
}
