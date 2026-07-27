$ErrorActionPreference = "Stop"
$repo = Split-Path -Parent $MyInvocation.MyCommand.Path
$tag = '  <script src="/assets/js/form-validation-en.js" defer></script>'
$changed = 0

Get-ChildItem $repo -Filter *.html -File -Recurse |
Where-Object { $_.FullName -notmatch '\\.git\\' } |
ForEach-Object {
    $content = Get-Content $_.FullName -Raw -Encoding UTF8
    if ($content -match '<form\b' -and $content -notmatch 'form-validation-en\.js' -and $content -match '</body>') {
        $content = $content -replace '</body>', "$tag`r`n</body>"
        Set-Content $_.FullName $content -Encoding UTF8
        Write-Host "Updated: $($_.Name)"
        $changed++
    }
}
Write-Host "Completed. Updated HTML files: $changed"
