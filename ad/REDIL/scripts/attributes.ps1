# REDIL lab - set account-level misconfiguration flags
# Runs on the DC (redil.local). Idempotent.
Import-Module ActiveDirectory

# --- AS-REP roastable users (Do not require Kerberos pre-authentication) -----
# These are foothold accounts for chains A and C (+ a legacy finance account).
$asrep = @("lucia.g", "noelia.s", "marcos.v")
foreach ($u in $asrep) {
    try {
        Get-ADUser -Identity $u | Set-ADAccountControl -DoesNotRequirePreAuth $true
        Write-Host "[+] AS-REP roastable set on $u"
    } catch { Write-Host "[-] $u not found: $_" }
}

# --- Password not required (weak legacy accounts) ----------------------------
$pwdnotreq = @("marcos.v", "raul.b")
foreach ($u in $pwdnotreq) {
    try {
        Set-ADUser -Identity $u -PasswordNotRequired $true
        Write-Host "[+] passwordnotreqd set on $u"
    } catch { Write-Host "[-] $u not found: $_" }
}
