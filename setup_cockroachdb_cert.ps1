# PowerShell script to download CockroachDB certificate
# Run this before running the migration script

# Create directory if it doesn't exist
$certDir = "$env:APPDATA\postgresql"
if (-not (Test-Path $certDir)) {
    New-Item -ItemType Directory -Path $certDir -Force
}

# Download certificate
$certUrl = "https://cockroachlabs.cloud/clusters/5ce4244a-90f1-4a00-9b6b-da01d25d67c2/cert"
$certPath = "$certDir\root.crt"

Write-Host "Downloading CockroachDB certificate..."
Invoke-WebRequest -Uri $certUrl -OutFile $certPath

if (Test-Path $certPath) {
    Write-Host "✓ Certificate downloaded successfully to: $certPath" -ForegroundColor Green
}
else {
    Write-Host "✗ Failed to download certificate" -ForegroundColor Red
    exit 1
}
