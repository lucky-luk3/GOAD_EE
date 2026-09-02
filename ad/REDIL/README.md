# REDIL — `redil.local`

A minimal, single-DC Active Directory lab modelling **Redil**, a mid-sized
Spanish cheese-making company (production, OT/SCADA, warehouse, sales, quality,
HR, finance…). It started as a family business and grew, so it accumulated
realistic misconfigurations.

The lab is designed for **GrexID**: it produces **long, convergent attack paths**
so the visual "alternative solutions / choke-point" analysis has something rich
to show.

## Design principles

- **One VM**: only the Domain Controller (like `GOAD-Mini`/`MINILAB`). All the
  identities (users, groups, OUs, ACLs, gMSA, ADCS template ACL) live on the DC,
  so ~60 identities cost a single machine.
- **English group names** (multi-market), **Spanish user logins**
  `name.<surname-initial>` (e.g. `lucia.g@redil.local`).
- **4 escalation chains, each ≥ 5 hops to Domain Admins.** No single choke point;
  several footholds and department members feed the same chains (more
  alternatives for GrexID to visualise).
- **No "everyone → Domain Admin" path.** The ADCS abuse is **ESC4 scoped to the
  `PKI Administrators` group only** — we deliberately do *not* publish GOAD's
  ESC1/ESC2/ESC9/ESC13 templates (those grant enrolment to `Domain Users`).

## Footholds (initial access)

| Account | How it's obtained |
|---------|-------------------|
| `lucia.g` | AS-REP roastable (HR) |
| `noelia.s` | AS-REP roastable (Sales) |
| `marcos.v` | AS-REP roastable + `passwordnotreqd` (Finance, legacy) |
| `svc_erp` | Kerberoastable (SPN `HTTP/erp.redil.local`) |
| `svc_sql`, `svc_web` | Kerberoastable service accounts |
| `oscar.p` | password hinted in `description` (OT operator) |

## The 4 escalation chains

**Chain A — HR → gMSA → password resets (5 hops)**
```
lucia.g ─MemberOf→ HR Payroll Admins ─ReadGMSAPassword→ gmsa_payroll$
        ─ForceChangePassword→ diego.m ─ForceChangePassword→ sergio.h
        ─AddSelf→ Domain Admins
```

**Chain B — ERP kerberoast → nested groups → server admins (6 hops)**
```
svc_erp ─MemberOf→ Database Administrators ─GenericWrite→ Backup Team
        ─GenericAll→ raul.b ─WriteDacl→ Server Administrators
        ─GenericAll→ admin.t0 (Domain Admin)
```

**Chain C — Sales → Purchasing → PKI → ADCS ESC4 (5 hops)**
```
noelia.s ─MemberOf→ Sales Department ─ForceChangePassword→ pablo.c
         ─GenericWrite(AddMember)→ PKI Administrators
         ─ADCSESC4 (control of a published template)→ Domain Admin
```

**Chain D — Production/OT → Maintenance → SCADA → GPO (5 hops)**
```
oscar.p ─MemberOf→ Production Operators ─GenericWrite→ Maintenance Engineers
        ─ForceChangePassword→ ivan.o ─WriteOwner→ GPO Managers
        ─WriteDacl→ Domain Admins
```

Every edge above is one that SharpHound collects and GrexID renders:
`MemberOf, ReadGMSAPassword, ForceChangePassword, GenericWrite, AddMember,
GenericAll, WriteDacl, WriteOwner, AddSelf, ADCSESC4`.

## Custom scripts (run on the DC, after AD data + ACLs)

- `scripts/attributes.ps1` — sets AS-REP roasting (`DoesNotRequirePreAuth`) and
  `passwordnotreqd` flags.
- `scripts/gmsa_readers.ps1` — grants `HR Payroll Admins` read access to the
  `gmsa_payroll` managed password → `ReadGMSAPassword` edge.
- `scripts/esc4.ps1` — grants `PKI Administrators` `GenericAll` over an existing
  published template (`User`) → scoped `ADCSESC4` edge.

## Deploy

```bash
# from the GOAD root
./goad.sh -t install -l REDIL -p virtualbox        # or -p vmware
```

The DC installs an Enterprise Root CA (needed for the ESC4 chain) but **web
enrolment / ESC8 is disabled** to keep the ADCS surface to the single scoped ESC4.

## Feed GrexID

Once deployed, run a SharpHound collection against `redil.local` and upload the
resulting ZIP to GrexID (SharpHound / BloodHound v6 ingestion). GrexID will then
surface the four chains, their shared intermediate nodes, and the alternative
mitigations.
