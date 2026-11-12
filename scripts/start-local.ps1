# Khởi động artifact local đã scan; không cần Python/Node trên host.
[CmdletBinding()]
param([switch]$PrepareOnly)
$ErrorActionPreference = 'Stop'
$workspace = Split-Path $PSScriptRoot -Parent
$existingRecord = Join-Path $workspace '.tools/local-demo.json'
if ((Test-Path -LiteralPath $existingRecord) -and -not $PrepareOnly) { throw 'An existing demo record is preserved at .tools/local-demo.json; use its compose_config and project to resume it' }
$manifestPath = Join-Path $workspace '.tools/local-images.json'
$provenance = Get-Content -Raw -Encoding utf8 (Join-Path $workspace '.tools/local-images-provenance.json') | ConvertFrom-Json
$artifactPath = [IO.Path]::GetFullPath((Join-Path $workspace $provenance.manifest))
if (-not $artifactPath.StartsWith($workspace + [IO.Path]::DirectorySeparatorChar, [StringComparison]::OrdinalIgnoreCase)) { throw 'Artifact path must stay in workspace' }
$receiptPath = Join-Path (Split-Path $artifactPath -Parent) 'local-policy-review.json'
$receipt = Get-Content -Raw -Encoding utf8 $receiptPath | ConvertFrom-Json
if ($receipt.status -ne 'LOCAL_POLICY_MATCH') { throw 'Local scan policy must be resolved before startup' }
if ([DateTimeOffset]::UtcNow -ge [DateTimeOffset]::Parse($receipt.policy_provenance.expires_at)) { throw 'Local approval expired' }
foreach ($proof in @(@($receipt.policy_provenance.approval,$receipt.policy_provenance.approval_sha256),@($receipt.policy_provenance.ledger,$receipt.policy_provenance.ledger_sha256))) {
    if ((Get-FileHash -LiteralPath (Join-Path $workspace $proof[0]) -Algorithm SHA256).Hash.ToLowerInvariant() -ne $proof[1]) { throw 'Local approval or policy changed; review again' }
}
foreach ($proof in $receipt.policy_provenance.additional_owner_decisions) {
    if ((Get-FileHash -LiteralPath (Join-Path $workspace $proof.decision) -Algorithm SHA256).Hash.ToLowerInvariant() -ne $proof.decision_sha256) { throw 'Additional approval changed or revoked' }
}
if ((Get-FileHash -LiteralPath $artifactPath -Algorithm SHA256).Hash.ToLowerInvariant() -ne $receipt.manifest_sha256) { throw 'Reviewed artifact manifest changed' }
$scanPath = Join-Path (Split-Path $artifactPath -Parent) 'candidate-security.json'
if ((Get-FileHash -LiteralPath $scanPath -Algorithm SHA256).Hash.ToLowerInvariant() -ne $receipt.scan_sha256) { throw 'Reviewed scan changed' }
$images = Get-Content -Raw -Encoding utf8 $manifestPath | ConvertFrom-Json
$mapping = @{ backend = 'backend'; frontend = 'frontend'; airflow = 'airflow'; postgres = 'postgres'; mysql = 'mysql' }
foreach ($kind in $mapping.Keys) {
    $approved = @($receipt.images | Where-Object target -eq $mapping[$kind])
    if ($approved.Count -ne 1 -or $approved[0].image_id -ne $images.$kind) { throw "Unreviewed image: $kind" }
    $actual = & podman image inspect $images.$kind --format '{{.Id}}'
    if ($LASTEXITCODE -ne 0 -or $actual.Trim() -ne $images.$kind) { throw "Missing local image: $kind" }
}
$env:PODMAN_COMPOSE_PROVIDER = Join-Path $workspace '.tools/docker-compose-5.6.0.exe'
$configText = & podman compose -f (Join-Path $workspace 'docker-compose.yml') --profile test config --format json
if ($LASTEXITCODE -ne 0) { throw 'Compose config failed' }
$config = $configText | ConvertFrom-Json
$project = 'aat-portable-demo-' + [Guid]::NewGuid().ToString('N').Substring(0,8)
$config.name = $project
foreach ($property in @($config.services.PSObject.Properties)) {
    $name = $property.Name
    if ($name -in @('backend-tests','e2e-tests') -or $name.StartsWith('regression-')) {
        $config.services.PSObject.Properties.Remove($name)
        continue
    }
    $service = $property.Value
    $kind = if ($name.StartsWith('airflow-')) { 'airflow' } elseif ($name -in @('backend','backend-worker','secrets-init','db-init','app-init')) { 'backend' } else { $name }
    $service.image = $images.$kind
    $service.PSObject.Properties.Remove('build')
    $service.PSObject.Properties.Remove('ports')
}
foreach ($entry in $config.volumes.PSObject.Properties) { $entry.Value.name = $project + '_' + $entry.Name }
foreach ($entry in $config.networks.PSObject.Properties) { $entry.Value.name = $project + '_' + $entry.Name }
foreach ($port in @(@('frontend',23000,80),@('backend',28000,8000),@('airflow-apiserver',28080,8080))) {
    $service = $config.services.($port[0])
    $service | Add-Member -NotePropertyName ports -NotePropertyValue @(@{host_ip='127.0.0.1';published=[string]$port[1];target=$port[2];protocol='tcp'})
    if (-not $PrepareOnly) {
        $listener = [Net.Sockets.TcpListener]::new([Net.IPAddress]::Loopback, $port[1])
        try { $listener.Start() } finally { $listener.Stop() }
    }
}
$config.services.backend.environment.AAT_ALLOWED_ORIGINS = 'http://frontend,http://localhost:23000,http://127.0.0.1:23000'
$config.services.backend.environment.AAT_AIRFLOW_PUBLIC_URL = 'http://localhost:28080'
$config.services.'airflow-apiserver'.environment.AIRFLOW__API__BASE_URL = 'http://localhost:28080'
$configPath = Join-Path $workspace ('.tools/compose-' + $project + '.json')
$config | ConvertTo-Json -Depth 100 | Set-Content -Encoding utf8 -LiteralPath $configPath
& podman compose -f $configPath -p $project config --quiet
if ($LASTEXITCODE -ne 0) { throw 'Prepared Compose config invalid' }
$record = @{project=$project;compose_config=$configPath;local_url='http://localhost:23000';airflow_url='http://localhost:28080';status='PREPARED_NOT_RUN';existing_services_modified=$false}
$recordPath = Join-Path $workspace '.tools/local-demo.json'
if ($PrepareOnly) { $record | ConvertTo-Json; return }
try {
    $record.status = 'STARTING'
    & podman compose -f $configPath -p $project up -d --no-build --wait --wait-timeout 240
    if ($LASTEXITCODE -ne 0) { throw 'Owned local demo did not become ready; inspect recorded project' }
    $health = Invoke-RestMethod 'http://127.0.0.1:28000/api/v1/health/ready' -TimeoutSec 15
    $record.status = 'READY'
    $record | ConvertTo-Json
} catch {
    $record.status = 'FAILED'
    throw
} finally {
    $record | ConvertTo-Json | Set-Content -Encoding utf8 -LiteralPath $recordPath
}
