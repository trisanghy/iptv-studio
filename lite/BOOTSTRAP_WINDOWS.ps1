# IPTV Studio: automatic, local-only Python bootstrap for Windows.
# Zero additional pip dependencies; signed-host HTTPS download with SHA-256 verification.
param([ValidateSet('gui','lite-install','lite-run','lite-status','lite-remove','lite-reschedule')][string]$Mode='gui')
$ErrorActionPreference = 'Stop'
$Project = Split-Path -Parent $MyInvocation.MyCommand.Path
$Runtime = Join-Path $Project 'runtime\python'
$Version = '3.13.17'
$HashByArch = @{
  'amd64' = '9e35319bffedab8b36ad44d8f377cb4f1733bcec257a0b6d04d94f01486ddb38'
  'arm64' = '7b58787a047b400edbfcb539aa3cdb4e2ed77bf0f22cae42b7c01cedd7dd6614'
  'win32' = '4afd37bc88ed1391209a4c58deb902cd0741a476692412b23d340aff6e9285e7'
}
function Test-Interpreter([string]$Path, [string[]]$Prefix) {
  try {
    $args1 = @(); $args1 += $Prefix; $args1 += @('-c','import sys,ssl,urllib.request; print("READY" if sys.version_info >= (3,10) else "OLD")')
    $result = & $Path @args1 2>$null
    if ($LASTEXITCODE -eq 0 -and ((@($result) -join "`n") -match 'READY')) {
      return $true
    }
  } catch { }
  return $false
}
function Find-Interpreter {
  $local = Join-Path $Runtime 'python.exe'
  if ((Test-Path -LiteralPath $local) -and (Test-Interpreter $local @())) {
    return @{ Path=$local; Prefix=@(); IsPortable=$true }
  }
  foreach($name in @('py','python','python3')) {
    $exe = Get-Command $name -ErrorAction SilentlyContinue
    if ($null -eq $exe) { continue }
    $prefix = @(); if($name -eq 'py') { $prefix = @('-3') }
    if (Test-Interpreter $exe.Source $prefix) {
      return @{ Path=$exe.Source; Prefix=$prefix; IsPortable=$false }
    }
  }
  return $null
}
function Install-LocalPython {
  Write-Host 'Khong tim thay Python 3 hop le. Dang tai Python chinh thuc ve THU MUC CHUONG TRINH...' -ForegroundColor Cyan
  $arch = 'amd64'
  try {
    $osArch = [System.Runtime.InteropServices.RuntimeInformation]::OSArchitecture.ToString().ToUpperInvariant()
    if ($osArch -eq 'ARM64') { $arch='arm64' }
    elseif($osArch -eq 'X86') { $arch='win32' }
  } catch {
    if ($env:PROCESSOR_ARCHITECTURE -eq 'ARM64') { $arch='arm64' }
    elseif(-not [Environment]::Is64BitOperatingSystem) { $arch='win32' }
  }
  $name = "python-$Version-embed-$arch.zip"
  $url = "https://www.python.org/ftp/python/$Version/$name"
  $root = Join-Path $Project 'runtime'
  New-Item -ItemType Directory -Force -Path $root | Out-Null
  $archive = Join-Path $root 'python-download.tmp.zip'
  $unpack = Join-Path $root 'python-unpack.tmp'
  if(Test-Path $unpack) { Remove-Item -Recurse -Force $unpack }
  try {
    [Net.ServicePointManager]::SecurityProtocol = [Net.ServicePointManager]::SecurityProtocol -bor [Net.SecurityProtocolType]::Tls12
    Write-Host "Nguon: $url"
    Invoke-WebRequest -Uri $url -OutFile $archive -UseBasicParsing -TimeoutSec 240
    if((Get-Item $archive).Length -lt 8000000) {throw 'Tep Python tai ve qua nho, co the la loi mang.'}
    $actual = (Get-FileHash -LiteralPath $archive -Algorithm SHA256).Hash.ToLowerInvariant()
    if($actual -ne $HashByArch[$arch]) {throw "SHA256 khong khop, DA HUY cai dat (khong chay file tai ve)."}
    Expand-Archive -LiteralPath $archive -DestinationPath $unpack -Force
    $python = Join-Path $unpack 'python.exe'
    $pythonw = Join-Path $unpack 'pythonw.exe'
    if(!(Test-Path $python) -or !(Test-Path $pythonw)) {throw 'Goi Python khong du file python.exe/pythonw.exe.'}
    # Embedded Python is isolated by default. Add the app directory for sibling imports.
    $pth = Join-Path $unpack 'python313._pth'
    @('python313.zip','.','..') | Set-Content -LiteralPath $pth -Encoding ASCII
    if (!(Test-Interpreter $python @())) {throw 'Python tu tai ve khong chay duoc (kiem tra bo Visual C++ runtime).'}
    if(Test-Path $Runtime) { Remove-Item -Recurse -Force $Runtime }
    Move-Item $unpack $Runtime
    Write-Host 'DA CAI PYTHON PORTABLE. Khong can quyen admin, khong sua PATH Windows.' -ForegroundColor Green
  } finally {
    Remove-Item -LiteralPath $archive -Force -ErrorAction SilentlyContinue
    if(Test-Path $unpack) {Remove-Item -LiteralPath $unpack -Recurse -Force -ErrorAction SilentlyContinue}
  }
}
try {
  $py=Find-Interpreter
  if ($null -eq $py) { Install-LocalPython; $py=Find-Interpreter }
  if ($null -eq $py) {throw 'Van khong the khoi dong Python. Kiem tra ket noi mang va Windows Security.'}
  # For Lite installed copies, prefer the stable local interpreter for all later commands.
  # The embedded ._pth deliberately isolates imports to its own installation folder.
  if (($Mode -ne 'gui') -and ($Mode -ne 'lite-install')) {
    $stable=Join-Path $env:LOCALAPPDATA 'IPTVStudioLite\runtime\python\python.exe'
    if ((Test-Path $stable) -and (Test-Interpreter $stable @())) {
      $py=@{ Path=$stable; Prefix=@(); IsPortable=$true }
    }
  }
  $entry = Join-Path $Project 'server.py'
  $argv=@()
  if ($Mode -ne 'gui') {
    $installed = Join-Path $env:LOCALAPPDATA 'IPTVStudioLite\cli.py'
    $entry = Join-Path $Project 'cli.py'
    if (($Mode -ne 'lite-install') -and (Test-Path -LiteralPath $installed)) {$entry = $installed}
    switch ($Mode) {
      'lite-install'    { $argv=@('install') }
      'lite-run'        { $argv=@('run','--no-publish') }
      'lite-status'     { $argv=@('status') }
      'lite-remove'     { $argv=@('remove-schedule') }
      'lite-reschedule' { $argv=@('reschedule') }
    }
  }
  if (!(Test-Path -LiteralPath $entry)) {throw "Khong tim thay file: $entry"}
  Write-Host "Dang chay: $Mode"
  $exeArgs=@(); $exeArgs+=@($py.Prefix); $exeArgs+=$entry; $exeArgs+=$argv
  & $py.Path @exeArgs
  exit $LASTEXITCODE
} catch {
  Write-Host "LOI KHOI DONG: $($_.Exception.Message)" -ForegroundColor Red
  exit 1
}
