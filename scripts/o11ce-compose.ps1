param(
  [Parameter(ValueFromRemainingArguments = $true)]
  [string[]]$ArgsPassthru
)

$candidates = @(
  (Join-Path (Get-Location) "compose.yml"),
  (Join-Path (Get-Location) "docker-compose.yml"),
  (Join-Path $HOME ".o11ce/stack/compose.yml")
)

$composeFile = $null
foreach ($p in $candidates) {
  if (Test-Path $p) { $composeFile = $p; break }
}

if (-not $composeFile) {
  Write-Host "No se encontró compose.yml. Busqué: $($candidates -join ', ')"
  exit 2
}

$workDir = Split-Path -Parent $composeFile

$docker = Get-Command docker -ErrorAction SilentlyContinue
$dc = Get-Command docker-compose -ErrorAction SilentlyContinue

$mode = $null
if ($docker) {
  try {
    & $docker.Source compose version *> $null
    $mode = "docker-compose-plugin"
  } catch {}
}
if (-not $mode -and $dc) { $mode = "docker-compose" }

if (-not $mode) {
  Write-Host "Docker Compose no encontrado (docker compose o docker-compose)"
  exit 2
}

Push-Location $workDir
try {
  if ($mode -eq "docker-compose-plugin") {
    & $docker.Source compose -f $composeFile @ArgsPassthru
    exit $LASTEXITCODE
  } else {
    & $dc.Source -f $composeFile @ArgsPassthru
    exit $LASTEXITCODE
  }
} finally {
  Pop-Location
}

