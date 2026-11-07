param([string]$RepoName = 'iptv-studio')
$ErrorActionPreference = 'Stop'
$Root = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$Owner = 'trisanghy'
if ($RepoName -notmatch '^[a-zA-Z0-9._-]+$') { throw 'Ten repository khong hop le' }
foreach ($Exe in @('git','gh')) {
  if (-not (Get-Command $Exe -ErrorAction SilentlyContinue)) { throw "Thieu $Exe. Hay cai Git va GitHub CLI truoc." }
}
Remove-Item Env:GH_TOKEN -ErrorAction SilentlyContinue
Remove-Item Env:GITHUB_TOKEN -ErrorAction SilentlyContinue
Remove-Item Env:GH_HOST -ErrorAction SilentlyContinue
$Actual = (& gh api user --jq '.login' | Out-String).Trim()
if ($LASTEXITCODE -ne 0 -or $Actual -ne $Owner) { throw "GitHub CLI dang dung '$Actual'; can '$Owner'. Chay: gh auth switch -h github.com -u trisanghy" }
if (Test-Path (Join-Path $Root '.git')) { throw 'Da co .git; khong ghi de. Dung lenh update sau khi kiem tra remote.' }
& gh repo view "$Owner/$RepoName" --json nameWithOwner 2>$null | Out-Null
if ($LASTEXITCODE -eq 0) { throw 'Repository da ton tai, khong ghi de.' }
Push-Location $Root
try {
  & git init -b main
  if ($LASTEXITCODE -ne 0) { throw 'git init that bai' }
  $GithubId = (& gh api user --jq '.id' | Out-String).Trim()
  & git config --local user.name $Owner
  & git config --local user.email "${GithubId}+${Owner}@users.noreply.github.com"
  & git add HUONG_DAN_DANG_GITHUB.md README.md .gitignore .gitattributes docs studio lite tools DANG_LEN_GITHUB_MAC.command DANG_LEN_GITHUB_WINDOWS.bat CAP_NHAT_MA_NGUON_MAC.command
  if ($LASTEXITCODE -ne 0) { throw 'git add that bai' }
  & git commit -m 'Initial source: IPTV Studio 5.2 + Lite 5.2'
  if ($LASTEXITCODE -ne 0) { throw 'git commit that bai' }
  & gh repo create "$Owner/$RepoName" --private --description 'IPTV Studio 5.2 and Lite: M3U management, multiround HLS checks, scheduled background updates' --source $Root --remote origin --push
  if ($LASTEXITCODE -ne 0) { throw 'Tao hoac push GitHub that bai. Khong tu tao repo moi.' }
  Write-Host "THANH CONG: https://github.com/$Owner/$RepoName" -ForegroundColor Green
} finally { Pop-Location }
