# REDIL lab - CHAIN A : allow the "HR Payroll Admins" group to read the
# gmsa_payroll managed password. This materialises a ReadGMSAPassword edge in
# BloodHound / GrexID (HR Payroll Admins -> gmsa_payroll$).
#
# The gmsa role creates the account with the DC as the only allowed reader;
# here we (re)set the principals to the HR Payroll Admins group so a human
# group - not just a computer - can retrieve the password.
Import-Module ActiveDirectory

$gmsaName = "gmsa_payroll"
$readerGroup = "HR Payroll Admins"

try {
    $grp = Get-ADGroup -Identity $readerGroup
    Set-ADServiceAccount -Identity $gmsaName -PrincipalsAllowedToRetrieveManagedPassword $grp.DistinguishedName
    Write-Host "[+] '$readerGroup' can now read the password of gMSA '$gmsaName'"
} catch {
    Write-Host "[-] Failed to set gMSA readers: $_"
}
