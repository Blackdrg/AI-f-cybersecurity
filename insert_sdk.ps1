$readmePath = "D:/AI-F/AI-f/README.md"
$sdkPath = "D:/AI-F/AI-f/sdk_insert.txt"

$readme = Get-Content $readmePath -Raw
$sdkContent = Get-Content $sdkPath -Raw

# Split into lines
$lines = $readme -split "`n"

# Line numbers (0-indexed for array): insert after line 1260 and 9376
# Note: array index equals line number minus 1
$insertPoints = @(1260, 9376)

$newLines = @()
for ($i = 0; $i -lt $lines.Count; $i++) {
    if ($insertPoints -contains $i) {
        $newLines += $sdkContent
    }
    $newLines += $lines[$i]
}

$newLines -join "`n" | Set-Content $readmePath -Encoding UTF8

Write-Host "SDK sections inserted at lines: $($insertPoints -join ', ')"
