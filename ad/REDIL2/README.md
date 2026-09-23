# REDIL2 — `redil.local` + one member server

**REDIL2 is identical to the [REDIL](../REDIL/README.md) lab** (same domain
`redil.local`, same ~213 identities, same 5 escalation paths, gMSA, scoped ADCS
ESC4, AdminSDHolder terminals, nested OU tree, weak-password test set) **plus one
minimal domain-joined Windows Server member**, with no extra services installed.

See `../REDIL/README.md` for the full attack-path and identity description; this
file only documents the difference.

## Why the extra machine

A single DC cannot show **lateral-movement / session** signals. Adding one member
server makes the lab collect the edges a real BloodHound/GrexID demo needs:

- **`AdminTo`** — `Server Administrators` are local admins on `REDILSRV01`.
- **`CanRDP`** — `IT Support` is in the server's *Remote Desktop Users*.
- **`HasSession`** — once someone logs on to the server, sessions appear.
- Ground for LAPS / RBCD / local-admin-reuse scenarios in the future.

## Machines

| Host | Role | Box | vCPU / RAM | IP |
|------|------|-----|-----------|-----|
| `REDIL2DC01` | DC `redil.local` (+ Enterprise CA) | `mayfly/windows_server2019` | 4 / 6144 | `.10` |
| `REDIL2SRV01` | Member server, **no services** | `mayfly/windows_server2019` | 2 / 2048 | `.21` |

The member server is the smallest sensible option: the same image the DC already
uses (no second multi-GB box to download; no Server Core box is published in the
project's box set), sized down to 2 vCPU / 2 GB. It is joined to the domain by the
standard GOAD mechanism — the `[server]` inventory group runs the `member_server`
role (`win_domain_membership`) in `ansible/ad-members.yml` — and moved into
`OU=Servers,OU=Admin,OU=REDIL`. Its VM/host names are distinct from REDIL
(`REDIL2DC01` / `REDIL2SRV01`) so both labs can coexist without a VirtualBox
name clash.

## Config difference

`data/config.json` adds one host:

```json
"srv01": {
  "hostname": "REDIL2SRV01",
  "type": "server",
  "local_admin_password": "Srv01-L0cal-Adm1n",
  "domain": "redil.local",
  "path": "OU=Servers,OU=Admin,OU=REDIL,DC=redil,DC=local",
  "use_laps": false,
  "local_groups": {
    "Administrators": ["REDIL\\Server Administrators"],
    "Remote Desktop Users": ["REDIL\\IT Support"]
  },
  "scripts": [],
  "vulns": ["disable_firewall"]
}
```

Inventories add `srv01` to `[domain]` and `[server]`; the providers add the
`REDILSRV01` box. Everything else is generated from the shared
`scripts/generate_config.py` (it writes both `ad/REDIL` and `ad/REDIL2`).

## Deploy

```bash
./goad.sh -t install -l REDIL2 -p virtualbox   # or -p vmware
```

Then run SharpHound against `redil.local` and upload the ZIP to GrexID.

> REDIL and REDIL2 use the same domain and DC IP, so run only one at a time.
