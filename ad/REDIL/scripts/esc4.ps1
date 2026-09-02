# REDIL lab - CHAIN C : ADCS ESC4 (scoped, NOT open to all Domain Users).
#
# We deliberately do NOT publish GOAD's vulnerable ESC1/ESC2/ESC9/ESC13 templates
# (those grant enrollment to "Domain Users" and would give EVERYONE a path to DA).
# Instead we reuse an already-published default template ("User") and grant only
# the "PKI Administrators" group write control (GenericAll) over it.
#
# A principal with write control over a published, enrollable template can
# reconfigure it (e.g. enable ENROLLEE_SUPPLIES_SUBJECT -> ESC1) and escalate to
# Domain Admin. SharpHound/BloodHound/GrexID materialise this as an ADCSESC4 edge
# originating from "PKI Administrators" only - not from Domain Users.
Import-Module ActiveDirectory

$controllerGroup = "PKI Administrators"
# Reuse an existing default template that the Enterprise CA already publishes.
$candidateTemplates = @("User", "WebServer", "Machine")

try {
    $configNC = (Get-ADRootDSE).configurationNamingContext
    $grp = Get-ADGroup -Identity $controllerGroup
    $sid = [System.Security.Principal.SecurityIdentifier]$grp.SID

    $done = $false
    foreach ($templateName in $candidateTemplates) {
        $templateDN = "CN=$templateName,CN=Certificate Templates,CN=Public Key Services,CN=Services,$configNC"
        if (-not (Test-Path "AD:\$templateDN")) { continue }

        $path = "AD:\$templateDN"
        $acl = Get-Acl -Path $path
        $ace = New-Object System.DirectoryServices.ActiveDirectoryAccessRule(
            $sid,
            [System.DirectoryServices.ActiveDirectoryRights]"GenericAll",
            [System.Security.AccessControl.AccessControlType]"Allow"
        )
        $acl.AddAccessRule($ace)
        Set-Acl -Path $path -AclObject $acl
        Write-Host "[+] '$controllerGroup' granted GenericAll over published template '$templateName' (ESC4, scoped)"
        $done = $true
        break
    }
    if (-not $done) { Write-Host "[-] No candidate template found to configure ESC4" }
} catch {
    Write-Host "[-] Failed to configure ESC4: $_"
}
