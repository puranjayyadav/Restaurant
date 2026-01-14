# Quick setup and run script for CockroachDB migration
# This script sets up the environment and runs the migration

Write-Host "=" * 60
Write-Host "CockroachDB Migration Setup"
Write-Host "=" * 60
Write-Host ""

# Step 1: Download certificate
Write-Host "Step 1: Downloading CockroachDB SSL certificate..."
$certDir = "$env:APPDATA\postgresql"
if (-not (Test-Path $certDir)) {
    New-Item -ItemType Directory -Path $certDir -Force | Out-Null
}

$certUrl = "https://cockroachlabs.cloud/clusters/5ce4244a-90f1-4a00-9b6b-da01d25d67c2/cert"
$certPath = "$certDir\root.crt"

try {
    Invoke-WebRequest -Uri $certUrl -OutFile $certPath -ErrorAction Stop
    Write-Host "✓ Certificate downloaded to: $certPath" -ForegroundColor Green
}
catch {
    Write-Host "✗ Failed to download certificate: $_" -ForegroundColor Red
    exit 1
}

# Step 2: Set environment variables
Write-Host ""
Write-Host "Step 2: Setting environment variables..."

# Check if Supabase credentials are set
if (-not $env:SUPABASE_URL -or -not $env:SUPABASE_KEY) {
    Write-Host "⚠ Warning: SUPABASE_URL and/or SUPABASE_KEY not set" -ForegroundColor Yellow
    Write-Host "Please set these environment variables before running the migration"
    Write-Host ""
}

# Set CockroachDB URL
$env:COCKROACHDB_URL = "postgresql://puranjay:Mo4MAznbTMcufpVAsU6Yzw@tailed-okapi-20468.j77.aws-us-east-1.cockroachlabs.cloud:26257/defaultdb?sslmode=verify-full"
Write-Host "✓ COCKROACHDB_URL set" -ForegroundColor Green

# Step 3: Run migration
Write-Host ""
Write-Host "Step 3: Running migration..."
Write-Host ""

python migrate_lemon8_to_cockroachdb.py

if ($LASTEXITCODE -eq 0) {
    Write-Host ""
    Write-Host "✓ Migration completed successfully!" -ForegroundColor Green
}
else {
    Write-Host ""
    Write-Host "✗ Migration failed. Check the error messages above." -ForegroundColor Red
    exit $LASTEXITCODE
}
