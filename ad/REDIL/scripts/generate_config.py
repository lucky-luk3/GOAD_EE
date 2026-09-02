#!/usr/bin/env python3
"""Generator for the REDIL GOAD lab config.json (redil.local, single DC).

Cheese company "Redil" - grew from a family business, so it accumulated
misconfigurations. Group names are in English (multi-market), user logins follow
the Spanish standard name.<surname-initial> (e.g. juan.g@redil.local).

Design goals:
  * 5 escalation paths to Domain Admins, each walkable by MANY people (the
    capability lives on department/team groups, not on a single user).
  * Paths CONVERGE (shared intermediate nodes) for a visually attractive graph;
    path E merges into path B at the "Backup Team" node.
  * Every edge is one SharpHound/BloodHound (and GrexID) materialises:
    MemberOf, ReadGMSAPassword, ForceChangePassword, GenericWrite, AddMember,
    GenericAll, WriteDacl, WriteOwner, AddSelf, ADCSESC4.
  * ADCS abuse is a SCOPED ESC4 (PKI Administrators only), never a Domain-Users
    path for everyone.
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
# Organisational Units
# ---------------------------------------------------------------------------
OUS = ["Tier0", "IT", "Servers", "Management", "HR", "Finance", "Sales",
       "Purchasing", "Production", "Maintenance", "Warehouse", "Quality",
       "Marketing", "ServiceAccounts"]
organisation_units = {ou: {"path": BASE} for ou in OUS}

# ---------------------------------------------------------------------------
# Groups (descriptive English names)
# ---------------------------------------------------------------------------
G = {
    "Tier0 Admins":            "Tier0",
    "Server Administrators":   "IT",
    "Database Administrators": "IT",
    "Backup Team":             "IT",
    "PKI Administrators":      "IT",
    "GPO Managers":            "IT",
    "IT Support":              "IT",
    "Helpdesk Operators":      "IT",
    "OT SCADA Admins":         "Maintenance",
    "Management Board":        "Management",
    "HR Department":           "HR",
    "HR Payroll Admins":       "HR",
    "Finance Department":      "Finance",
    "Sales Department":        "Sales",
    "Purchasing Department":   "Purchasing",
    "Production Operators":    "Production",
    "Maintenance Engineers":   "Maintenance",
    "Warehouse Staff":         "Warehouse",
    "Quality Lab":             "Quality",
    "Marketing Team":          "Marketing",
    "Service Accounts":        "ServiceAccounts",
}
groups = {
    "universal": {},
    "global": {name: {"path": ou_path(ou)} for name, ou in G.items()},
    "domainlocal": {},
}

# ---------------------------------------------------------------------------
# Users
# ---------------------------------------------------------------------------
users = {}
_used = set()

FIRST = ["Juan", "Maria", "Antonio", "Carmen", "Jose", "Ana", "Manuel", "Laura",
         "Francisco", "Isabel", "David", "Sara", "Javier", "Elena", "Daniel",
         "Rosa", "Sergio", "Marta", "Miguel", "Cristina", "Angel", "Nuria",
         "Pedro", "Beatriz", "Luis", "Patricia", "Alberto", "Silvia", "Ruben",
         "Andrea", "Alvaro", "Raquel", "Adrian", "Natalia", "Ivan", "Paula",
         "Victor", "Alicia", "Jorge", "Irene", "Hector", "Lorena", "Ramon",
         "Teresa", "Gonzalo", "Monica", "Emilio", "Sonia", "Ismael", "Vega"]
SUR = ["Lopez", "Diaz", "Ramos", "Gil", "Serrano", "Molina", "Blanco", "Suarez",
       "Nunez", "Iglesias", "Medina", "Cortes", "Santos", "Marin", "Cabrera",
       "Reyes", "Vargas", "Campos", "Vela", "Leon", "Herrera", "Cano",
       "Guerrero", "Rubio", "Soto", "Bravo", "Crespo", "Duran", "Lorenzo",
       "Roman", "Pardo", "Aguilar", "Mora", "Vidal", "Rojas", "Carrasco",
       "Gallego", "Franco", "Montero", "Prieto", "Calvo", "Navarro", "Ibanez",
       "Gimenez", "Ferrer", "Saez", "Pascual", "Vicente", "Hidalgo", "Mendez"]
_ni = 0

def _login(first, sur):
    base = f"{first.lower()}.{sur[0].lower()}"
    if base not in _used:
        return base
    base2 = f"{first.lower()}.{sur[:2].lower()}"
    if base2 not in _used:
        return base2
    i = 2
    while f"{base}{i}" in _used:
        i += 1
    return f"{base}{i}"

def add_user(login, first, surname, dept_ou, dept_groups, password,
             description="-", spns=None, extra=None):
    entry = {"firstname": first, "surname": surname, "password": password,
             "city": "Villalon de Campos", "description": description,
             "groups": list(dept_groups), "path": ou_path(dept_ou)}
    if spns:
        entry["spns"] = spns
    if extra:
        entry.update(entry.pop("__none__", {}) or {}); entry.update(extra)
    users[login] = entry
    _used.add(login)
    return login

def add_team(n, dept_ou, dept_groups, year=2020, desc=None):
    """Add n filler employees to an OU + groups, return their logins."""
    global _ni
    out = []
    for _ in range(n):
        first = FIRST[_ni % len(FIRST)]
        sur = SUR[(_ni * 13 + 5) % len(SUR)]
        _ni += 1
        login = _login(first, sur)
        pwd = f"{first}{sur}{year + (_ni % 6)}"
        d = desc or (dept_groups[0] + " - empleado")
        add_user(login, first, sur, dept_ou, list(dept_groups), pwd, d)
        out.append(login)
    return out

# --- Tier 0 (Domain Admins) -------------------------------------------------
add_user("carlos.f", "Carlos", "Fernandez", "Management",
         ["Management Board", "Tier0 Admins", "Domain Admins"],
         "QuesoManchego1975",
         "Fundador y CEO - cuenta historica con privilegios de dominio")
add_user("admin.t0", "Alberto", "Tejedor", "Tier0",
         ["Tier0 Admins", "Domain Admins"], "T0-P4ssw0rd-Adm!n",
         "Administrador de dominio (IT)")

# ===========================================================================
# CHAIN A  -  HR team (5) -> gMSA -> password resets -> Helpdesk -> DA
# ===========================================================================
# The whole "HR Payroll Admins" team (5 people) can read the payroll gMSA.
hr_payroll = []
hr_payroll.append(add_user("lucia.g", "Lucia", "Garcia", "HR",
    ["HR Department", "HR Payroll Admins"], "Lucia2021",
    "Responsable de nominas (AS-REP roastable)"))
hr_payroll.append(add_user("marta.b", "Marta", "Blanco", "HR",
    ["HR Department", "HR Payroll Admins"], "Marta2020",
    "Tecnico de nominas (AS-REP roastable)"))
hr_payroll += add_team(3, "HR", ["HR Department", "HR Payroll Admins"], 2019,
                       "Tecnico de nominas")
# normal HR user the gMSA can reset
add_user("diego.m", "Diego", "Moreno", "HR", ["HR Department"],
         "Diego.Moreno.88", "Auxiliar de RRHH")
# helpdesk admin that diego.m can reset; can add self to Domain Admins
add_user("sergio.h", "Sergio", "Herrero", "IT",
         ["IT Support", "Helpdesk Operators"], "H3lpd3sk!2023",
         "Administrador de soporte (helpdesk)")
add_team(4, "HR", ["HR Department"], 2018)  # extra HR staff (no path)

# ===========================================================================
# CHAIN B  -  ERP kerberoast -> DBAs -> Backup Team -> Server Admins -> DA
# ===========================================================================
add_user("svc_erp", "Service", "ERP", "ServiceAccounts",
         ["Service Accounts", "Database Administrators"], "Erp$vc_2019",
         "Cuenta de servicio del ERP (SAP legacy)",
         spns=["HTTP/erp.redil.local", "HTTP/erp"])
add_team(2, "IT", ["IT Support", "Database Administrators"], 2020,
         "Administrador de bases de datos")
add_user("raul.b", "Raul", "Benitez", "IT", ["IT Support"],
         "Raul.Benitez.2020", "Tecnico de sistemas (junior)")
add_team(2, "IT", ["IT Support", "Server Administrators"], 2021,
         "Administrador de servidores")

# ===========================================================================
# CHAIN C  -  Sales team (8) -> Purchasing -> PKI -> ADCS ESC4 (scoped) -> DA
# ===========================================================================
add_user("noelia.s", "Noelia", "Sanz", "Sales", ["Sales Department"],
         "Noelia2022", "Comercial de zona norte (AS-REP roastable)")
add_user("emilio.c", "Emilio", "Cortes", "Sales", ["Sales Department"],
         "Emilio2021", "Comercial de exportacion (AS-REP roastable)")
add_team(6, "Sales", ["Sales Department"], 2019, "Comercial")
add_user("pablo.c", "Pablo", "Castro", "Purchasing", ["Purchasing Department"],
         "Pablo.Castro.91", "Responsable de compras")
add_team(3, "Purchasing", ["Purchasing Department"], 2020, "Tecnico de compras")
add_user("hugo.p", "Hugo", "Prieto", "IT", ["IT Support", "PKI Administrators"],
         "PkiAdm!n_2023", "Administrador de la PKI interna")
add_team(1, "IT", ["IT Support", "PKI Administrators"], 2022,
         "Administrador de la PKI interna")

# ===========================================================================
# CHAIN D  -  Production (15) -> Maintenance Engineers (4) -> SCADA -> GPO -> DA
# ===========================================================================
prod_ops = add_team(15, "Production", ["Production Operators"], 2018,
                    "Operario de produccion (linea de curado)")
maint_eng = add_team(4, "Maintenance", ["Maintenance Engineers"], 2019,
                     "Ingeniero de mantenimiento industrial")
add_user("ivan.o", "Ivan", "Ortega", "Maintenance", ["OT SCADA Admins"],
         "Sc4da_Maint#21", "Ingeniero SCADA / OT (cuenta privilegiada)")
add_team(2, "IT", ["GPO Managers", "IT Support"], 2021,
         "Gestor de politicas de grupo (GPO)")

# ===========================================================================
# CHAIN E  -  Finance team (6) -> backup.svc -> [merges into Backup Team] -> B
# ===========================================================================
add_user("marcos.v", "Marcos", "Vega", "Finance", ["Finance Department"],
         "Marcos2020", "Contable senior (cuenta antigua, sin preautenticacion)")
add_team(5, "Finance", ["Finance Department"], 2019, "Contable")
add_user("backup.svc", "Service", "Backup", "ServiceAccounts",
         ["Service Accounts", "Backup Team"], "B4ckup$vc!",
         "Cuenta de servicio de copias (Veeam) - miembro de Backup Team")
add_team(1, "IT", ["IT Support", "Backup Team"], 2020,
         "Operador de copias de seguridad")

# --- other service accounts (kerberoastable) & departments (no path) -------
add_user("svc_sql", "Service", "SQL", "ServiceAccounts", ["Service Accounts"],
         "Sql$vc-2018", "Cuenta de servicio MSSQL (reporting)",
         spns=["MSSQLSvc/sql.redil.local:1433", "MSSQLSvc/sql.redil.local"])
add_user("svc_web", "Service", "Web", "ServiceAccounts", ["Service Accounts"],
         "W3b$vc_2020", "Cuenta de servicio del portal de pedidos",
         spns=["HTTP/pedidos.redil.local"])
add_team(8, "Warehouse", ["Warehouse Staff"], 2018, "Operario de almacen")
add_team(5, "Quality", ["Quality Lab"], 2019, "Tecnico de laboratorio/calidad")
add_team(4, "Marketing", ["Marketing Team"], 2020, "Tecnico de marketing")
add_team(2, "Management", ["Management Board"], 2017, "Direccion")

# ===========================================================================
# REALISM POPULATION  -  accounts & groups WITHOUT any path to Domain Admin.
# Reflects a real, well-intentioned but not-very-mature company: department OUs
# exist, service/shared/contractor/disabled accounts are separated, role and
# resource groups are used - but structure is a bit inconsistent (some groups in
# a central "Groups" OU, some still in department OUs).
# Goal: keep users with a DA path at ~20-30% of the company.
# ===========================================================================
# --- extra organisational units (good intention, moderate maturity) --------
for _ou in ["Contractors", "SharedAccounts", "DisabledAccounts", "Groups"]:
    OUS.append(_ou)
    organisation_units[_ou] = {"path": BASE}

# --- benign groups (role + resource + distribution), all in OU=Groups -------
BENIGN_GROUPS = [
    # department sub-role groups (people, no escalation ACE)
    "Production Line Workers", "Production Shift Leaders", "Logistics & Transport",
    "Quality Auditors", "Customer Service", "Sales Back Office",
    "Accounts Payable", "Accounts Receivable", "Maintenance Technicians",
    "Digital Marketing", "Service Desk L1", "IT Interns", "Facilities & Cleaning",
    "Reception", "R&D New Products", "External Contractors",
    # resource / access groups (membership only, used on apps/shares/VPN)
    "VPN Users", "Remote Access Users", "WiFi Corporate", "ERP Users",
    "CAD Software Users", "Fileshare Finance RW", "Fileshare Finance RO",
    "Fileshare Production RW", "Fileshare Quality RW", "SharePoint Contributors",
    "SharePoint Readers", "Office Printer Admins",
    # distribution / org-wide
    "All Staff", "All Managers", "Department Heads",
]
for _g in BENIGN_GROUPS:
    groups["global"][_g] = {"path": ou_path("Groups")}

# --- path-less population across the company --------------------------------
add_team(40, "Production", ["Production Line Workers"], 2016, "Operario de linea (envasado/curado)")
add_team(5,  "Production", ["Production Shift Leaders"], 2017, "Jefe de turno de produccion")
add_team(12, "Warehouse",  ["Logistics & Transport"], 2018, "Logistica y transporte")
add_team(5,  "Quality",    ["Quality Auditors"], 2019, "Auditor de calidad / APPCC")
add_team(10, "Sales",      ["Customer Service"], 2019, "Atencion al cliente")
add_team(4,  "Sales",      ["Sales Back Office"], 2020, "Back office comercial")
add_team(4,  "Finance",    ["Accounts Payable"], 2019, "Cuentas a pagar")
add_team(3,  "Finance",    ["Accounts Receivable"], 2020, "Cuentas a cobrar")
add_team(6,  "Maintenance", ["Maintenance Technicians"], 2018, "Tecnico de mantenimiento")
add_team(3,  "Marketing",  ["Digital Marketing"], 2021, "Marketing digital")
add_team(4,  "IT",         ["Service Desk L1"], 2021, "Tecnico de soporte nivel 1")
add_team(2,  "IT",         ["IT Interns"], 2022, "Becario de IT")
add_team(4,  "Management", ["Facilities & Cleaning"], 2018, "Servicios generales")
add_team(2,  "Management", ["Reception"], 2019, "Recepcion")
add_team(5,  "Quality",    ["R&D New Products"], 2020, "I+D nuevos productos")
add_team(8,  "Contractors", ["External Contractors"], 2022, "Contratista externo (temporal)")

# --- shared / generic accounts (a real company always has these) -----------
add_user("svc_scanner", "Scanner", "MFP", "SharedAccounts", ["Service Accounts"],
         "Sc4nn3r-MFP!", "Cuenta de escaner / multifuncion (SMB)")
add_user("shared.info", "Buzon", "Info", "SharedAccounts", [],
         "Inf0-M@ilb0x", "Buzon compartido info@redil.local")
add_user("shared.pedidos", "Buzon", "Pedidos", "SharedAccounts", [],
         "P3d1d0s-M@il", "Buzon compartido pedidos@redil.local")
add_user("reception.pc", "PC", "Recepcion", "SharedAccounts", ["Reception"],
         "R3cepc10n-PC", "Cuenta compartida del PC de recepcion")

# --- disabled leaver accounts (disabled by scripts/attributes.ps1) ----------
leavers = add_team(5, "DisabledAccounts", [], 2015, "Baja - empleado que ya no trabaja aqui")

# --- membership mesh: benign role/resource/DL memberships (adds realism,
#     never escalation). Applied to every user based on their OU. ------------
def _ou_of(login):
    p = users[login]["path"]
    return p.split(",")[0].replace("OU=", "")

office_ous = {"Sales", "Finance", "HR", "Marketing", "Purchasing", "IT", "Management", "Tier0"}
for login, u in list(users.items()):
    ou = _ou_of(login)
    grps = u["groups"]
    if ou == "DisabledAccounts":
        continue
    if "All Staff" not in grps:
        grps.append("All Staff")
    if ou in office_ous:
        grps += ["ERP Users", "VPN Users", "WiFi Corporate"]
    if ou in {"Production", "Maintenance", "Warehouse", "Quality"}:
        grps.append("WiFi Corporate")
    if ou == "Finance":
        grps.append("Fileshare Finance RW")
    if ou in {"Production", "Maintenance"}:
        grps.append("Fileshare Production RW")
    if ou in {"Maintenance"}:
        grps.append("CAD Software Users")
    if ou == "Quality":
        grps.append("Fileshare Quality RW")
    # de-duplicate, keep order
    seen = set(); u["groups"] = [g for g in grps if not (g in seen or seen.add(g))]

# department heads / managers (well-intentioned RBAC) -> benign DL ownership
for _mgr in ["carlos.f", "admin.t0"]:
    users[_mgr]["groups"].append("All Managers")
    users[_mgr]["groups"].append("Department Heads")

# ---------------------------------------------------------------------------
# gMSA (payroll). HR Payroll Admins is granted read via scripts/gmsa_readers.ps1
# ---------------------------------------------------------------------------
gmsa = {"gmsa_payroll": {"gMSA_Name": "gmsa_payroll",
                         "gMSA_FQDN": "gmsa_payroll.redil.local",
                         "gMSA_SPNs": ["HTTP/payroll.redil.local"],
                         "gMSA_HostNames": [DC_HOSTNAME]}}

# ---------------------------------------------------------------------------
# ACLs = the edges of the escalation paths
# ---------------------------------------------------------------------------
acls = {}
def ace(name, for_, to, right, inheritance="None"):
    acls[name] = {"for": for_, "to": to, "right": right, "inheritance": inheritance}

# CHAIN A (ReadGMSAPassword edge set by scripts/gmsa_readers.ps1)
ace("A_gmsa_fcp_diego",       "gmsa_payroll$", "diego.m", "Ext-User-Force-Change-Password")
ace("A_diego_fcp_sergio",     "diego.m", "sergio.h", "Ext-User-Force-Change-Password")
ace("A_sergio_addself_da",    "sergio.h", "Domain Admins", "Ext-Self-Self-Membership")

# CHAIN B
ace("B_dba_gw_backup",        "Database Administrators", "Backup Team", "GenericWrite")
ace("B_backup_ga_raul",       "Backup Team", "raul.b", "GenericAll")
ace("B_raul_wd_serveradmins", "raul.b", "Server Administrators", "WriteDacl")
ace("B_serveradmins_ga_t0",   "Server Administrators", "admin.t0", "GenericAll")

# CHAIN C (ADCSESC4 edge set by scripts/esc4.ps1)
ace("C_sales_fcp_pablo",      "Sales Department", "pablo.c", "Ext-User-Force-Change-Password")
ace("C_pablo_gw_pki",         "pablo.c", "PKI Administrators", "GenericWrite")

# CHAIN D
ace("D_prod_gw_maint",        "Production Operators", "Maintenance Engineers", "GenericWrite")
ace("D_maint_fcp_ivan",       "Maintenance Engineers", "ivan.o", "Ext-User-Force-Change-Password")
ace("D_ivan_gw_scada",        "ivan.o", "OT SCADA Admins", "GenericWrite")
ace("D_scada_wo_gpo",         "OT SCADA Admins", "GPO Managers", "WriteOwner")
ace("D_gpo_wd_da",            "GPO Managers", "Domain Admins", "WriteDacl")

# CHAIN E : Finance team -> backup.svc, which is a member of Backup Team
#           => the path MERGES into CHAIN B at the "Backup Team" node.
ace("E_finance_fcp_backupsvc", "Finance Department", "backup.svc", "Ext-User-Force-Change-Password")

# --- BENIGN, NON-ESCALATING ACLs (roles with real permissions over objects,
#     but every target is path-less, so they add NO route to Domain Admin) ---
# Service Desk L1 can reset passwords of warehouse staff (operational only).
ace("bg_servicedesk_fcp_warehouse", "Service Desk L1",
    f"OU=Warehouse,{BASE}", "Ext-User-Force-Change-Password", "All")
# "All Managers" owns/manages the "All Staff" distribution list (add/remove).
ace("bg_managers_ga_allstaff", "All Managers", "All Staff", "GenericAll")
# Department Heads can read (only) the Sales OU (reporting visibility).
ace("bg_depthead_read_sales", "Department Heads", f"OU=Sales,{BASE}",
    "ReadProperty", "All")
# HR Department can read staff objects in Marketing OU (benign HR visibility).
ace("bg_hr_read_marketing", "HR Department", f"OU=Marketing,{BASE}",
    "ReadProperty", "All")

# ---------------------------------------------------------------------------
config = {
    "lab": {
        "hosts": {
            "dc01": {
                "hostname": DC_HOSTNAME, "type": "dc",
                "local_admin_password": DOMAIN_PASSWORD, "domain": DOMAIN,
                "path": BASE,
                "scripts": ["attributes.ps1", "gmsa_readers.ps1", "esc4.ps1"],
                "vulns": ["disable_firewall"],
            }
        },
        "domains": {
            DOMAIN: {
                "dc": "dc01", "domain_password": DOMAIN_PASSWORD,
                "netbios_name": NETBIOS, "ca_server": "dc01",
                "ca_web_enrollment": False, "trust": "",
                "laps_path": f"OU=Servers,{BASE}",
                "organisation_units": organisation_units, "groups": groups,
                "multi_domain_groups_member": [], "gmsa": gmsa,
                "acls": acls, "users": users,
            }
        },
    }
}

if __name__ == "__main__":
    with open("/home/user/GOAD_EE/ad/REDIL/data/config.json", "w",
              encoding="utf-8") as f:
        json.dump(config, f, indent=4, ensure_ascii=False)
    print("users:", len(users), "groups:", len(groups["global"]),
          "ous:", len(organisation_units), "acls:", len(acls))
