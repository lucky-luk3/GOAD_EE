# REDIL — `redil.local`

A minimal, single-DC Active Directory lab modelling **Redil**, a mid-sized
Spanish cheese-making company (production, OT/SCADA, warehouse, sales, quality,
HR, finance…). It started as a family business and grew, so it accumulated
realistic misconfigurations.

The lab is designed for **GrexID**: it produces **long, convergent attack paths**
walkable by **many people** so the visual "alternative solutions / choke-point"
analysis has a rich, attractive graph to show.

## Design principles

- **One VM**: only the Domain Controller (like `GOAD-Mini`/`MINILAB`). All the
  identities (users, groups, OUs, ACLs, gMSA, ADCS template ACL) live on the DC,
  so ~210 identities cost a single machine.
- **Realistic company, not just attack paths.** ~205 active employees across all
  departments, plus service/shared/contractor accounts and disabled leavers.
  **Only ~27% of active users have any path to Domain Admin** — the rest are
  ordinary staff. Many role/resource/distribution groups (VPN, ERP, file shares,
  SharePoint, "All Staff", department sub-teams) and a few benign, scoped
  permissions (e.g. Service Desk L1 resets only warehouse users; "All Managers"
  owns the "All Staff" DL) exist **without** creating any escalation — the kind
  of well-intentioned-but-imperfect RBAC a real, still-maturing IT team builds.
- **English group names** (multi-market), **Spanish user logins**
  `name.<surname-initial>` (e.g. `lucia.g@redil.local`).
- **5 escalation paths, each ≥ 5 hops to Domain Admins, walkable by MANY people.**
  The escalation capability lives on **department/team groups**, not on single
  users: e.g. the whole 5-person `HR Payroll Admins` team walks Chain A, all 15
  `Production Operators` walk Chain D. ~43 low-privilege users have a ≥5-hop path.
- **Paths converge** on a few choke groups (great for GrexID's choke-point view),
  and **Chain E merges into Chain B at the `Backup Team` node**.
- **No "everyone → Domain Admin" path.** The ADCS abuse is **ESC4 scoped to the
  `PKI Administrators` group only** — we deliberately do *not* publish GOAD's
  ESC1/ESC2/ESC9/ESC13 templates (those grant enrolment to `Domain Users`).

## Footholds (initial access) — several per path, so many people can start

| Account(s) | How it's obtained |
|---------|-------------------|
| `lucia.g`, `marta.b` | AS-REP roastable (HR Payroll Admins) |
| `noelia.s`, `emilio.c` | AS-REP roastable (Sales) |
| `marcos.v` | AS-REP roastable + `passwordnotreqd` (Finance, legacy) |
| `svc_erp` | Kerberoastable (SPN `HTTP/erp.redil.local`) |
| `svc_sql`, `svc_web` | Kerberoastable service accounts |
| Production operators | password hinted in `description` / weak reused creds |

Any compromised member of an entry team walks the whole path, so a single
mitigation rarely closes a path — exactly what GrexID's alternatives view shows.

## The 5 escalation paths

**Chain A — HR Payroll team (5 people) → gMSA → password resets (5 hops)**
```
<HR Payroll Admins, 5 members> ─ReadGMSAPassword→ gmsa_payroll$
        ─ForceChangePassword→ diego.m ─ForceChangePassword→ sergio.h
        ─GenericAll (via AdminSDHolder)→ Domain Admins
```

**Chain B — ERP kerberoast → nested groups → server admins (5 hops)**
```
svc_erp ─MemberOf→ Database Administrators ─GenericWrite→ Backup Team
        ─GenericAll→ raul.b ─WriteDacl→ Server Administrators
        ─GenericAll (via AdminSDHolder)→ Domain Admins
```

**Chain C — Sales team (8) → Purchasing → PKI → ADCS ESC4 (5 hops)**
```
<Sales Department, 8 members> ─ForceChangePassword→ pablo.c
         ─GenericWrite(AddMember)→ PKI Administrators
         ─ADCSESC4 (control of a published template)→ Domain Admin
```

**Chain D — Production (15) → Maintenance Engineers (4) → SCADA → GPO (6 hops)**
```
<Production Operators, 15 members> ─GenericWrite→ Maintenance Engineers (4)
        ─ForceChangePassword→ ivan.o ─GenericWrite→ OT SCADA Admins
        ─WriteOwner→ GPO Managers ─GenericAll (via AdminSDHolder)→ Domain Admins
```

**Chain E — Finance team (6) → backup.svc → MERGES INTO Chain B (6 hops)**
```
<Finance Department, 6 members> ─ForceChangePassword→ backup.svc
        ─MemberOf→ Backup Team  ◀── merge point with Chain B
        ─GenericAll→ raul.b ─WriteDacl→ Server Administrators
        ─GenericAll (via AdminSDHolder)→ Domain Admins
```

`Backup Team` is the shared junction: both the ERP path (B) and the Finance
path (E) funnel through it, so the graph shows a clear convergence.

Every edge above is one that SharpHound collects and GrexID renders:
`MemberOf, ReadGMSAPassword, ForceChangePassword, GenericWrite, AddMember,
GenericAll, WriteDacl, WriteOwner, ADCSESC4` (terminal DA control via AdminSDHolder).

## Attack-path graph

```mermaid
flowchart LR
    DA(["Domain Admins"]):::sink

    %% ---------- Chain A : HR / gMSA ----------
    A0["HR Payroll Admins (5)<br/>lucia.g, marta.b, ..."]:::entry
    A1["gmsa_payroll$"]
    A2["diego.m"]
    A3["sergio.h<br/>(Helpdesk)"]
    A0 -->|"ReadGMSAPassword"| A1
    A1 -->|"ForceChangePassword"| A2
    A2 -->|"ForceChangePassword"| A3
    A3 -->|"GenericAll<br/>(AdminSDHolder)"| DA

    %% ---------- Chain B : ERP kerberoast ----------
    B0["svc_erp<br/>(Kerberoast)"]:::entry
    B1["Database Administrators"]
    BK["Backup Team"]:::merge
    B2["raul.b"]
    B3["Server Administrators"]
    B0 -->|"MemberOf"| B1
    B1 -->|"GenericWrite"| BK
    BK -->|"GenericAll"| B2
    B2 -->|"WriteDacl"| B3
    B3 -->|"GenericAll<br/>(AdminSDHolder)"| DA

    %% ---------- Chain C : ADCS ESC4 ----------
    C0["Sales Department (8)<br/>noelia.s, emilio.c, ..."]:::entry
    C1["pablo.c"]
    C2["PKI Administrators"]
    C3["User cert template"]
    C0 -->|"ForceChangePassword"| C1
    C1 -->|"GenericWrite / AddMember"| C2
    C2 -->|"ADCSESC4"| C3
    C3 -->|"enroll → forge cert"| DA

    %% ---------- Chain D : Production / OT ----------
    D0["Production Operators (15)"]:::entry
    D1["Maintenance Engineers (4)"]
    D2["ivan.o<br/>(SCADA)"]
    D3["OT SCADA Admins"]
    D4["GPO Managers"]
    D0 -->|"GenericWrite"| D1
    D1 -->|"ForceChangePassword"| D2
    D2 -->|"GenericWrite"| D3
    D3 -->|"WriteOwner"| D4
    D4 -->|"GenericAll<br/>(AdminSDHolder)"| DA

    %% ---------- Chain E : Finance (merges into B) ----------
    E0["Finance Department (6)<br/>marcos.v, ..."]:::entry
    E1["backup.svc"]
    E0 -->|"ForceChangePassword"| E1
    E1 -->|"MemberOf"| BK

    classDef entry fill:#1e5f2e,stroke:#0d3d19,color:#fff;
    classDef merge fill:#8a5a00,stroke:#5c3c00,color:#fff;
    classDef sink fill:#7a1020,stroke:#4d0a14,color:#fff;
```

Green = initial-access teams (many people share each path) · amber = `Backup Team`,
the shared junction where Chains B and E converge · red = the `Domain Admins`
target.

## Organisational structure & benign roles

Department OUs (`Production`, `Warehouse`, `Sales`, `Finance`, `HR`, `Quality`,
`Maintenance`, `Purchasing`, `Marketing`, `Management`, `IT`, `Tier0`) plus
org-wide OUs the admin created with good intent: `ServiceAccounts`,
`SharedAccounts`, `Contractors`, `DisabledAccounts`, `Groups`. Structure is
deliberately a bit inconsistent (some groups in `OU=Groups`, the original ones
still in department OUs) — a company that is maturing, not fully mature.

Benign, **non-escalating** groups and permissions (present for realism, none of
them reach Domain Admin):

- **Role sub-teams**: Production Line Workers, Shift Leaders, Logistics &
  Transport, Quality Auditors, Customer Service, Accounts Payable/Receivable,
  Maintenance Technicians, Service Desk L1, R&D New Products, Reception…
- **Resource/access groups**: VPN Users, WiFi Corporate, ERP Users, CAD Software
  Users, Fileshare RW/RO groups, SharePoint Contributors/Readers, Office Printer
  Admins.
- **Distribution/org**: All Staff, All Managers, Department Heads.
- **Scoped operational permissions** (lateral, never to DA): `Service Desk L1`
  can reset passwords of `OU=Warehouse` users only; `All Managers` has
  `GenericAll` over the `All Staff` distribution list; `Department Heads`/`HR`
  have read-only visibility over certain OUs.

## Password / dictionary test set

~14% of accounts carry deliberately weak passwords — some typical dictionary
entries (`Password123`, `Verano2024`…) and some derived from the local context
(Palencia, Villalón de Campos, Tierra de Campos and nearby monuments:
`Villalon2024`, `RolloDeVillalon`, `PataDeMula`, `CristoDelOtero`,
`CanalDeCastilla`, `LaOlmeda2024`…). This is meant to exercise **GrexID's
dictionary generation and password audit**. See `PASSWORD_TESTSET.md` for the
seed terms and the ground-truth crackable accounts. Several sit on
AS-REP/kerberoastable footholds, so cracking them leads straight into a chain.

## Custom scripts (run on the DC, after AD data + ACLs)

- `scripts/attributes.ps1` — sets AS-REP roasting (`DoesNotRequirePreAuth`) and
  `passwordnotreqd` flags.
- `scripts/gmsa_readers.ps1` — grants `HR Payroll Admins` read access to the
  `gmsa_payroll` managed password → `ReadGMSAPassword` edge.

Two ESC/edge behaviours are proper GOAD vuln roles, configured from `config.json`
(`vulns` + `vulns_vars`) and run as the domain admin (`become: runas`):

- `vulns/adcs_esc4` (modelled on `vulns/adcs_esc7`) grants `PKI Administrators`
  `GenericAll` over the published `User` template → scoped `ADCSESC4` edge. It
  must run elevated: modifying a default template's DACL needs Enterprise Admin
  rights (a plain script running as `vagrant` fails with "Access is denied").
- `vulns/adminsdholder` grants the terminal principals of Chains A, B/E and D
  (`sergio.h`, `Server Administrators`, `GPO Managers`) `GenericAll` over the
  **AdminSDHolder** object and then **forces SDProp**. This is how GOAD makes a
  durable `GenericAll → Domain Admins` edge (cf. `lord.varys`): a direct ACE on
  the protected `Domain Admins` group is reverted by SDProp every ~60 min, but an
  ACE on AdminSDHolder is *copied onto* every protected group by SDProp, so it
  persists and materialises as a real `GenericAll → Domain Admins` edge. The
  direct `GenericAll → Domain Admins` ACEs are also set in `config.json` (for the
  immediate edge, GOAD-style); forcing SDProp makes the propagated copy appear at
  once instead of waiting up to an hour.

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
