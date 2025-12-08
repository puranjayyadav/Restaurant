# Quick test script for featured itineraries endpoint

$url = "http://localhost:8000/api/discovery/featured-itineraries/?limit=8"

Write-Host "Testing endpoint: $url" -ForegroundColor Cyan
Write-Host ""

try {
    $response = Invoke-WebRequest -Uri $url -Method GET -ErrorAction Stop
    
    Write-Host "Status Code: $($response.StatusCode)" -ForegroundColor Green
    Write-Host ""
    Write-Host "Response:" -ForegroundColor Yellow
    
    # Parse and pretty-print JSON
    $json = $response.Content | ConvertFrom-Json
    $json | ConvertTo-Json -Depth 10
    
    Write-Host ""
    Write-Host "Total Featured Itineraries: $($json.total_featured)" -ForegroundColor Green
} catch {
    Write-Host "Error: $_" -ForegroundColor Red
    Write-Host "Make sure Django server is running on port 8000" -ForegroundColor Yellow
}

