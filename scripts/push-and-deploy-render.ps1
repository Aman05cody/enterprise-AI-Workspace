# Prepare git + push to GitHub so Render Blueprint can deploy
# Run from anywhere: powershell -ExecutionPolicy Bypass -File scripts\push-and-deploy-render.ps1

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
if (-not (Test-Path (Join-Path $Root "render.yaml"))) {
  $Root = "C:\Users\Aman\OneDrive\Desktop\enterprise-ai-workspace"
}
Set-Location $Root
Write-Host "Project: $Root" -ForegroundColor Cyan

if (-not (Get-Command git -ErrorAction SilentlyContinue)) {
  throw "git not found. Install Git for Windows first."
}
if (-not (Get-Command gh -ErrorAction SilentlyContinue)) {
  throw "gh not found. Install GitHub CLI first."
}

# Auth check
$auth = gh auth status 2>&1 | Out-String
if ($auth -match "not logged") {
  Write-Host "`nYou need to log into GitHub. A browser window will open..." -ForegroundColor Yellow
  gh auth login -h github.com -p https -w
}

if (-not (Test-Path ".git")) {
  git init
  git branch -M main
}

# Ensure we don't commit secrets
if (Test-Path ".env") {
  Write-Host "Note: .env is gitignored (good)." -ForegroundColor DarkGray
}

git add -A
$status = git status --porcelain
if ($status) {
  git commit -m "Deploy: Enterprise AI Workspace ready for Render"
} else {
  Write-Host "Nothing new to commit." -ForegroundColor DarkGray
}

$remotes = git remote 2>$null
if (-not $remotes) {
  Write-Host "Creating private GitHub repo enterprise-ai-workspace..." -ForegroundColor Cyan
  gh repo create enterprise-ai-workspace --private --source=. --remote=origin --push
} else {
  Write-Host "Pushing to origin..." -ForegroundColor Cyan
  git push -u origin main
}

$repoUrl = gh repo view --json url -q .url 2>$null
Write-Host "`n✅ Code is on GitHub: $repoUrl" -ForegroundColor Green
Write-Host "`nNext (2 minutes in browser):" -ForegroundColor Yellow
Write-Host "  1. Open https://dashboard.render.com"
Write-Host "  2. New → Blueprint → select this repo"
Write-Host "  3. Apply render.yaml"
Write-Host "  4. Wait for eaw-api + eaw-web to go Live"
Write-Host "`nGuide: docs\RENDER.md"
if ($repoUrl) { Start-Process $repoUrl }
Start-Process "https://dashboard.render.com/select-repo?type=blueprint"
