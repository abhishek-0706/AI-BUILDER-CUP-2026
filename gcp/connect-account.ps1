param(
  [Parameter(Mandatory=$true)][string]$Account,
  [string]$ProjectId
)
$ErrorActionPreference = 'Stop'
$repoRoot = Split-Path -Parent $PSScriptRoot
$portableRoot = Join-Path $repoRoot 'tmp\cloud-tools\google-cloud-sdk'
$portableCloud = Join-Path $portableRoot 'bin\gcloud.cmd'
$cloudCommand = Get-Command gcloud -ErrorAction SilentlyContinue
if ($cloudCommand) { $cloudCli = $cloudCommand.Source }
elseif (Test-Path -LiteralPath $portableCloud) { $cloudCli = $portableCloud }
else { throw 'Install Google Cloud CLI first: https://docs.cloud.google.com/sdk/docs/install-sdk' }
$previousPython = $env:CLOUDSDK_PYTHON
$previousBqPython = $env:CLOUDSDK_BQ_PYTHON
try {
  $bundledPython = Join-Path $portableRoot 'platform\bundledpython\python.exe'
  if (Test-Path -LiteralPath $bundledPython) {
    $env:CLOUDSDK_PYTHON = $bundledPython
    $env:CLOUDSDK_BQ_PYTHON = $bundledPython
  }
  $knownAccounts = & $cloudCli auth list '--format=value(account)'
  if ($knownAccounts -notcontains $Account) {
    & $cloudCli auth login $Account --brief
    if ($LASTEXITCODE -ne 0) { throw 'Google sign-in did not complete.' }
  }
  & $cloudCli projects list --account=$Account '--filter=lifecycleState:ACTIVE' '--format=table(projectId,name)'
  if ($LASTEXITCODE -ne 0) { throw 'Could not list projects for this Google account.' }
  if ($ProjectId) {
    & $cloudCli projects describe $ProjectId --account=$Account '--format=value(projectId)'
    if ($LASTEXITCODE -ne 0) { throw 'The selected project is not accessible to this account.' }
    & $cloudCli config set account $Account
    & $cloudCli config set project $ProjectId
    $billingRaw = & $cloudCli billing projects describe $ProjectId --account=$Account '--format=json'
    if ($LASTEXITCODE -ne 0) { Write-Warning 'Check billing access in Google Cloud Console before deployment.' }
    else {
      $billing = $billingRaw | ConvertFrom-Json
      if (-not $billing.billingEnabled) { Write-Warning 'Billing is not enabled. Link billing in Google Cloud Console before deployment.' }
      else { Write-Host 'Billing is enabled for the selected project.' }
    }
  } else {
    Write-Host 'Choose an accessible project and rerun with -ProjectId YOUR_PROJECT_ID.'
    Write-Host 'If no project appears, create one at https://console.cloud.google.com/projectcreate and link billing.'
  }
} finally {
  $env:CLOUDSDK_PYTHON = $previousPython
  $env:CLOUDSDK_BQ_PYTHON = $previousBqPython
}
