param(
    [string]$OutFile,
    [string]$Urls
)

$ErrorActionPreference = "Stop"

# Handle comma-separated string input for better compatibility with CMD
$UrlList = $Urls -split ',' | ForEach-Object { $_.Trim() }

foreach ($Url in $UrlList) {
    if ([string]::IsNullOrWhiteSpace($Url)) { continue }
    
    Write-Host "Trying to download from: $Url"
    try {
        # Create directory if it doesn't exist
        $Dir = [System.IO.Path]::GetDirectoryName($OutFile)
        if (-not (Test-Path $Dir)) {
            New-Item -ItemType Directory -Path $Dir | Out-Null
        }

        # Use .NET WebClient for better compatibility and speed in some cases, or sticking to Invoke-WebRequest
        # Invoke-WebRequest shows a progress bar by default in PS 5.1
        Invoke-WebRequest -Uri $Url -OutFile $OutFile -TimeoutSec 60
        
        if (Test-Path $OutFile) {
            $size = (Get-Item $OutFile).Length
            if ($size -gt 1024) { # Simple check: file should be larger than 1KB (avoid empty error pages)
                Write-Host "Download success!"
                exit 0
            } else {
                Write-Warning "File too small ($size bytes), possible error page."
                Remove-Item $OutFile -Force
            }
        }
    } catch {
        Write-Warning "Failed to download from $Url. Error: $_"
        if (Test-Path $OutFile) {
            Remove-Item $OutFile -Force
        }
    }
}

Write-Error "All download attempts failed."
exit 1
