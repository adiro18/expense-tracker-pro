# Smoke test + load generator for Grafana (Windows PowerShell 5.1 / PowerShell 7).
# Usage: .\scripts\smoke_test.ps1 -BaseUrl http://localhost:8000 -Requests 200
param(
  [string]$BaseUrl = "http://localhost:8000",
  [int]$Requests = 200
)
$BaseUrl = $BaseUrl.TrimEnd('/')
$fail = $false

function Check($Path, $Expected, $Text) {
  # curl.exe ships with Windows 10/11 and behaves the same as on Linux
  $out = & curl.exe -s -m 10 -w "`n%{http_code}" "$BaseUrl$Path"
  $code = ($out | Select-Object -Last 1)
  $body = ($out | Select-Object -SkipLast 1) -join "`n"
  if ($code -eq "$Expected" -and (-not $Text -or $body.Contains($Text))) {
    Write-Host "  PASS  $Path -> $code"
  } else {
    Write-Host "  FAIL  $Path -> $code (expected $Expected $Text)"; $script:fail = $true
  }
}

Write-Host "Smoke testing $BaseUrl"
Check "/health/live" 200 '"alive"'
Check "/health/ready" 200 '"ready"'
Check "/metrics" 200 "http_requests_total"
Check "/auth/login" 200 "Log in"

Write-Host "Generating $Requests requests for Grafana..."
$paths = @("/health/live", "/health/ready", "/auth/login", "/auth/register", "/", "/does-not-exist")
for ($i = 0; $i -lt $Requests; $i++) {
  & curl.exe -s -o NUL -m 10 "$BaseUrl$($paths[$i % $paths.Count])" | Out-Null
}
$total = 0
(& curl.exe -s "$BaseUrl/metrics") -split "`n" | Where-Object { $_ -like "http_requests_total*" } |
  ForEach-Object { $total += [double]($_ -split " ")[-1] }
Write-Host "Done. http_requests_total = $total"
if ($fail) { exit 1 }
