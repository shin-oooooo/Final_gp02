<#
.SYNOPSIS
  Stops processes that are LISTENING on common Dash / Flask dev ports for this repo.

.NOTES
  Intentionally does NOT terminate every python.exe on the machine (that would break
  editors, venvs, and unrelated work). Use this after codegen when multiple agents
  left stray servers on the same ports.
#>
$ErrorActionPreference = "SilentlyContinue"
$ports = @(8050, 8051, 8060, 8061, 8071, 8072)
$myPid = $PID

foreach ($port in $ports) {
  $conns = Get-NetTCPConnection -State Listen -LocalPort $port -ErrorAction SilentlyContinue
  foreach ($c in $conns) {
    $op = [int]$c.OwningProcess
    if ($op -gt 0 -and $op -ne $myPid) {
      Stop-Process -Id $op -Force -ErrorAction SilentlyContinue
      Write-Host "Stopped PID $op (port $port)"
    }
  }
}
Write-Host "Port cleanup done."
