#!/usr/bin/env python3
"""Generator for the REDIL GOAD lab config.json (redil.local, single DC).

Cheese company "Redil" - grew from a family business, so it accumulated
misconfigurations. Group names are in English (multi-market), user logins follow
the Spanish standard name.<surname-initial> (e.g. juan.g@redil.local).

Design goal: 4 LONG escalation chains (>= 5 hops) to Domain Admins, using only
edges that SharpHound/BloodHound (and therefore GrexID) actually materialise:
MemberOf, ReadGMSAPassword, ForceChangePassword, GenericWrite/AddMember,
GenericAll, WriteDacl, WriteOwner, AddSelf, ADCSESC4.
"""
import json

DOMAIN = "redil.local"
NETBIOS = "REDIL"
BASE = "DC=redil,DC=local"
DOMAIN_PASSWORD = "R3dilQu3s0s#2024!"
DC_HOSTNAME = "REDILDC01"

def ou_path(*ous):
    return ",".join([f"OU={o}" for o in ous] + [BASE])

# ---------------------------------------------------------------------------
# Organisational Units (departments of the company)
# ---------------------------------------------------------------------------
OUS = [
    "Tier0", "IT", "Servers", "Management", "HR", "Finance", "Sales",
    "Purchasing", "Production", "Maintenance", "Warehouse", "Quality",
    "Marketing", "ServiceAccounts",
]
organisation_units = {ou: {"path": BASE} for ou in OUS}

# ---------------------------------------------------------------------------
# Groups (descriptive English names). Global scope unless stated.
# ---------------------------------------------------------------------------
G = {
    # Tier 0 / IT privileged
    "Tier0 Admins":            ou_path("Tier0"),
    "Server Administrators":   ou_path("IT"),
    "Database Administrators": ou_path("IT"),
    "Backup Team":             ou_path("IT"),
    "PKI Administrators":      ou_path("IT"),
    "GPO Managers":            ou_path("IT"),
    "IT Support":              ou_path("IT"),
    "Helpdesk Operators":      ou_path("IT"),
    # Business departments
    "Management Board":        ou_path("Management"),
    "HR Department":           ou_path("HR"),
    "HR Payroll Admins":       ou_path("HR"),
    "Finance Department":      ou_path("Finance"),
    "Sales Department":        ou_path("Sales"),
    "Purchasing Department":   ou_path("Purchasing"),
    "Production Operators":    ou_path("Production"),
    "Maintenance Engineers":   ou_path("Maintenance"),
    "Maintenance Staff":       ou_path("Maintenance"),
    "OT SCADA Admins":         ou_path("Maintenance"),
    "Warehouse Staff":         ou_path("Warehouse"),
    "Quality Lab":             ou_path("Quality"),
    "Marketing Team":          ou_path("Marketing"),
    "Service Accounts":        ou_path("ServiceAccounts"),
}
groups = {
    "universal": {},
    "global": {name: {"path": path} for name, path in G.items()},
    "domainlocal": {},
}
# Tier0 Admins is nested into the builtin Domain Admins (real escalation target)
groups["global"]["Tier0 Admins"]["members"] = []  # membership handled via users

# ---------------------------------------------------------------------------
# Users
# ---------------------------------------------------------------------------
users = {}

def add_user(login, first, surname, dept_ou, dept_groups, password,
             description="-", spns=None, extra=None):
    entry = {
        "firstname": first,
        "surname": surname,
        "password": password,
        "city": "Villalon de Campos",
        "description": description,
        "groups": list(dept_groups),
        "path": ou_path(dept_ou),
    }
    if spns:
        entry["spns"] = spns
    if extra:
        entry.update(extra)
    users[login] = entry

# --- Tier 0 (Domain Admins) -------------------------------------------------
# Founder of the family business, still Domain Admin (legacy, weak-ish habits)
add_user("carlos.f", "Carlos", "Fernandez", "Management",
         ["Management Board", "Tier0 Admins", "Domain Admins"],
         "QuesoManchego1975",
         "Fundador y CEO - cuenta historica con privilegios de dominio")
# Current IT lead, also Domain Admin
add_user("admin.t0", "Alberto", "Tejedor", "Tier0",
         ["Tier0 Admins", "Domain Admins"], "T0-P4ssw0rd-Adm!n",
         "Administrador de dominio (IT)")

# --- CHAIN A actors (HR / gMSA) --------------------------------------------
# lucia.g : foothold, AS-REP roastable (flag set by attributes.ps1)
add_user("lucia.g", "Lucia", "Garcia", "HR",
         ["HR Department", "HR Payroll Admins"], "Lucia2021",
         "Tecnico de nominas")
# diego.m : normal HR user whose password the gMSA can reset
add_user("diego.m", "Diego", "Moreno", "HR",
         ["HR Department"], "Diego.Moreno.88", "Auxiliar de RRHH")
# sergio.h : helpdesk admin user that diego.m can reset; can add self to DA
add_user("sergio.h", "Sergio", "Herrero", "IT",
         ["IT Support", "Helpdesk Operators"], "H3lpd3sk!2023",
         "Administrador de soporte (helpdesk)")

# --- CHAIN B actors (ERP kerberoast -> DB -> Backup -> Server Admins) -------
add_user("svc_erp", "Service", "ERP", "ServiceAccounts",
         ["Service Accounts", "Database Administrators"], "Erp$vc_2019",
         "Cuenta de servicio del ERP (SAP legacy)",
         spns=["HTTP/erp.redil.local", "HTTP/erp"])
add_user("raul.b", "Raul", "Benitez", "IT",
         ["IT Support"], "Raul.Benitez.2020",
         "Tecnico de sistemas (junior)")

# --- CHAIN C actors (Sales AS-REP -> Purchasing -> PKI -> ADCS ESC4) -------
add_user("noelia.s", "Noelia", "Sanz", "Sales",
         ["Sales Department"], "Noelia2022",
         "Comercial de zona norte")
add_user("pablo.c", "Pablo", "Castro", "Purchasing",
         ["Purchasing Department"], "Pablo.Castro.91",
         "Responsable de compras")
# a PKI admin already in the group (so the ESC4 template ACE has an owner group)
add_user("hugo.p", "Hugo", "Prieto", "IT",
         ["IT Support", "PKI Administrators"], "PkiAdm!n_2023",
         "Administrador de la PKI interna")

# --- CHAIN D actors (Production/OT -> Maintenance -> SCADA -> GPO -> DA) ----
add_user("oscar.p", "Oscar", "Pastor", "Production",
         ["Production Operators"], "Verano2024",
         "Operario de produccion (linea de curado). (pwd temporal: Verano2024)")
add_user("ivan.o", "Ivan", "Ortega", "Maintenance",
         ["Maintenance Engineers", "OT SCADA Admins"], "Sc4da_Maint#21",
         "Ingeniero de mantenimiento industrial / SCADA")

# --- extra misconfig accounts ----------------------------------------------
add_user("svc_sql", "Service", "SQL", "ServiceAccounts",
         ["Service Accounts"], "Sql$vc-2018",
         "Cuenta de servicio MSSQL (reporting)",
         spns=["MSSQLSvc/sql.redil.local:1433", "MSSQLSvc/sql.redil.local"])
add_user("svc_web", "Service", "Web", "ServiceAccounts",
         ["Service Accounts"], "W3b$vc_2020",
         "Cuenta de servicio del portal web de pedidos",
         spns=["HTTP/pedidos.redil.local"])
add_user("marcos.v", "Marcos", "Vega", "Finance",
         ["Finance Department"], "Marcos2020",
         "Contable - cuenta antigua sin preautenticacion")
add_user("backup.svc", "Service", "Backup", "ServiceAccounts",
         ["Service Accounts", "Backup Team"], "B4ckup$vc!",
         "Cuenta de servicio de copias de seguridad (Veeam)")

# ---------------------------------------------------------------------------
# Filler users (no escalation path) - realistic department population
# ---------------------------------------------------------------------------
FIRST = ["Juan", "Maria", "Antonio", "Carmen", "Jose", "Ana", "Manuel",
         "Laura", "Francisco", "Isabel", "David", "Sara", "Javier", "Elena",
         "Daniel", "Rosa", "Sergio", "Marta", "Miguel", "Cristina", "Angel",
         "Nuria", "Pedro", "Beatriz", "Luis", "Patricia", "Alberto", "Silvia",
         "Ruben", "Andrea", "Alvaro", "Raquel", "Adrian", "Natalia", "Ivan",
         "Paula", "Victor", "Alicia", "Jorge", "Irene"]
SUR = ["Lopez", "Diaz", "Ramos", "Gil", "Serrano", "Molina", "Blanco",
       "Suarez", "Nunez", "Iglesias", "Medina", "Cortes", "Santos", "Marin",
       "Cabrera", "Reyes", "Vargas", "Campos", "Vela", "Leon", "Herrera",
       "Peña", "Cano", "Guerrero", "Rubio", "Soto", "Bravo", "Crespo",
       "Duran", "Lorenzo", "Roman", "Pardo", "Aguilar", "Mora", "Vidal",
       "Rojas", "Carrasco", "Gallego", "Franco", "Montero"]
FILLER_DEPTS = [
    ("Production", "Production Operators", 8),
    ("Warehouse", "Warehouse Staff", 6),
    ("Sales", "Sales Department", 6),
    ("Quality", "Quality Lab", 4),
    ("Finance", "Finance Department", 3),
    ("HR", "HR Department", 3),
    ("Marketing", "Marketing Team", 3),
    ("Purchasing", "Purchasing Department", 3),
    ("Maintenance", "Maintenance Staff", 4),
    ("Management", "Management Board", 2),
    ("IT", "IT Support", 3),
]
idx = 0
used = set(users.keys())
for ou, grp, n in FILLER_DEPTS:
    made = 0
    while made < n:
        first = FIRST[idx % len(FIRST)]
        sur = SUR[(idx * 7 + 3) % len(SUR)]
        idx += 1
        login = f"{first.lower()}.{sur[0].lower()}"
        if login in used:
            login = f"{first.lower()}.{sur[:2].lower()}"
        if login in used:
            continue
        used.add(login)
        pwd = f"{first}{sur}{2018 + (idx % 7)}"
        add_user(login, first, sur, ou, [grp], pwd, f"{grp} - empleado")
        made += 1

# ---------------------------------------------------------------------------
# gMSA account (payroll). Created before ad-acl, so it can be an ACE 'for'.
# gMSA_HostNames must be an existing computer -> the DC.
# HR Payroll Admins is granted read via scripts/gmsa_readers.ps1 (ReadGMSAPassword edge).
# ---------------------------------------------------------------------------
gmsa = {
    "gmsa_payroll": {
        "gMSA_Name": "gmsa_payroll",
        "gMSA_FQDN": "gmsa_payroll.redil.local",
        "gMSA_SPNs": ["HTTP/payroll.redil.local"],
        "gMSA_HostNames": [DC_HOSTNAME],
    }
}

# ---------------------------------------------------------------------------
# ACLs = the edges of the escalation chains
# right values supported by the acl role:
#   GenericAll, GenericWrite, WriteDacl, WriteOwner, WriteProperty, Self, ...
#   Ext-User-Force-Change-Password, Ext-Self-Self-Membership, Ext-Write-Self-Membership
# ---------------------------------------------------------------------------
acls = {}

def ace(name, for_, to, right, inheritance="None"):
    acls[name] = {"for": for_, "to": to, "right": right, "inheritance": inheritance}

# ---- CHAIN A : lucia.g -> HR Payroll Admins -[ReadGMSA]-> gmsa_payroll$
#      -> diego.m -> sergio.h -> Domain Admins  (5 hops) --------------------
# (ReadGMSAPassword edge is set by scripts/gmsa_readers.ps1)
ace("A_gmsa_fcp_diego", "gmsa_payroll$", "diego.m", "Ext-User-Force-Change-Password")
ace("A_diego_fcp_sergio", "diego.m", "sergio.h", "Ext-User-Force-Change-Password")
ace("A_sergio_addself_da", "sergio.h", "Domain Admins", "Ext-Self-Self-Membership")

# ---- CHAIN B : svc_erp -> Database Administrators -[GenericWrite]-> Backup Team
#      -> Backup Team -[GenericAll]-> raul.b -> [WriteDacl] Server Administrators
#      -> Server Administrators -[GenericAll]-> admin.t0 (Domain Admin)  (5 hops)
ace("B_dba_gw_backup", "Database Administrators", "Backup Team", "GenericWrite")
ace("B_backup_ga_raul", "Backup Team", "raul.b", "GenericAll")
ace("B_raul_wd_serveradmins", "raul.b", "Server Administrators", "WriteDacl")
ace("B_serveradmins_ga_admint0", "Server Administrators", "admin.t0", "GenericAll")

# ---- CHAIN C : noelia.s -> Sales Department -[FCP]-> pablo.c
#      -> pablo.c -[GenericWrite/AddMember]-> PKI Administrators
#      -> PKI Administrators -[ADCSESC4]-> ESC4 template -> Domain Admin  (>=5 hops)
# (ADCSESC4 edge is set by scripts/esc4.ps1 granting GenericAll on the ESC4 template)
ace("C_sales_fcp_pablo", "Sales Department", "pablo.c", "Ext-User-Force-Change-Password")
ace("C_pablo_gw_pki", "pablo.c", "PKI Administrators", "GenericWrite")

# ---- CHAIN D : oscar.p -> Production Operators -[GenericWrite]-> Maintenance Engineers
#      -> Maintenance Engineers -[FCP]-> ivan.o -> [WriteOwner] GPO Managers
#      -> GPO Managers -[WriteDacl]-> Domain Admins  (5 hops) -----------------
ace("D_prod_gw_maint", "Production Operators", "Maintenance Engineers", "GenericWrite")
ace("D_maint_fcp_ivan", "Maintenance Engineers", "ivan.o", "Ext-User-Force-Change-Password")
ace("D_ivan_wo_gpomgr", "ivan.o", "GPO Managers", "WriteOwner")
ace("D_gpomgr_wd_da", "GPO Managers", "Domain Admins", "WriteDacl")

# ---------------------------------------------------------------------------
# Assemble
# ---------------------------------------------------------------------------
config = {
    "lab": {
        "hosts": {
            "dc01": {
                "hostname": DC_HOSTNAME,
                "type": "dc",
                "local_admin_password": DOMAIN_PASSWORD,
                "domain": DOMAIN,
                "path": BASE,
                "scripts": [
                    "attributes.ps1",     # AS-REP roastable + passwordnotreqd flags
                    "gmsa_readers.ps1",   # HR Payroll Admins -> ReadGMSAPassword
                    "esc4.ps1",           # PKI Administrators -> ADCSESC4 on template
                ],
                "vulns": ["disable_firewall"],
            }
        },
        "domains": {
            DOMAIN: {
                "dc": "dc01",
                "domain_password": DOMAIN_PASSWORD,
                "netbios_name": NETBIOS,
                "ca_server": "dc01",
                "ca_web_enrollment": False,
                "trust": "",
                "laps_path": f"OU=Servers,{BASE}",
                "organisation_units": organisation_units,
                "groups": groups,
                "multi_domain_groups_member": [],
                "gmsa": gmsa,
                "acls": acls,
                "users": users,
            }
        },
    }
}

with open("/home/user/GOAD_EE/ad/REDIL/data/config.json", "w", encoding="utf-8") as f:
    json.dump(config, f, indent=4, ensure_ascii=False)

print("users:", len(users))
print("groups:", len(groups["global"]))
print("ous:", len(organisation_units))
print("acls:", len(acls))
print("DA members:", [u for u, v in users.items() if "Domain Admins" in v["groups"]])
