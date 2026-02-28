# Скрипт обновления лендинга при новом релизе
# Использование: .\update-landing.ps1 -Version "1.0.1" -User "yourusername" -Repo "c14"
param(
    [Parameter(Mandatory=$true)]
    [string]$Version,
    [Parameter(Mandatory=$true)]
    [string]$User,
    [Parameter(Mandatory=$true)]
    [string]$Repo
)

$indexPath = Join-Path $PSScriptRoot "..\index.html"
$content = Get-Content $indexPath -Raw -Encoding UTF8

$content = $content -replace 'v\d+\.\d+\.\d+', "v$Version"
$content = $content -replace 'ChatList-\d+\.\d+\.\d+-setup\.exe', "ChatList-$Version-setup.exe"
$content = $content -replace 'ChatList \d+\.\d+\.\d+', "ChatList $Version"
$content = $content -replace 'USER', $User
$content = $content -replace 'REPO', $Repo

Set-Content $indexPath $content -Encoding UTF8 -NoNewline
Write-Host "Обновлено: версия $Version, $User/$Repo"
