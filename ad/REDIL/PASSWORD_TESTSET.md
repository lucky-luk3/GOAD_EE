# REDIL — Password / dictionary test set

A subset of accounts (~14% of the domain, **not** everyone) is seeded with weak
passwords so you can exercise **GrexID's dictionary generation and password
audit** end-to-end: generate a wordlist from the company's context, crack the
NTLM hashes (from the collection / DCSync), and confirm GrexID reports them.

The remaining ~86% of users keep `Name+Surname+Year` style passwords (also a
useful pattern to test rule-based mutation), and privileged/service accounts
mostly keep non-dictionary passwords.

## Seed terms a good generator should include

- **Company**: `Redil`, `redil.local`, cheese / `queso`.
- **Location**: `Villalon` (Villalón de Campos), `Palencia`, `TierraDeCampos`,
  `Campos`, `Valladolid`, `Castilla`.
- **Local heritage / monuments**: `RolloDeVillalon` (El Rollo of Villalón),
  `PataDeMula` / `QuesoDeVillalon` (the local cheese), `CristoDelOtero`,
  `CanalDeCastilla`, `LaOlmeda` (Roman villa), `Fromista`, `ParedesDeNava`,
  `Becerril`, `Carrion` (Carrión de los Condes), `Ampudia`, `Palomares`
  (dovecotes), `CalleMayor`, `CampoGotico`.
- **Common mutations**: `+2024/2023/2022`, capitalised first letter, `1`/`123`
  suffixes, seasons (`Verano`, `Invierno`, `Primavera`, `Otono`).
- **Generic dictionary**: `Password123`, `Qwerty123`, `Bienvenido1`, `Admin1234`,
  `Cambiame1`, `Usuario2024`, `Empresa2024`.

## Expected-crackable accounts (ground truth)

Regional / heritage themed:

| Account | Password | Note |
|---------|----------|------|
| `lucia.g` | `Palencia2024` | HR Payroll (AS-REP) → Chain A |
| `marta.b` | `Villalon2024` | HR Payroll (AS-REP) → Chain A |
| `emilio.c` | `PataDeMula` | Sales (AS-REP) → Chain C |
| others | `TierraDeCampos`, `CristoDelOtero`, `RolloDeVillalon`, `QuesoDeVillalon`, `CanalDeCastilla`, `Fromista2024`, `ParedesDeNava`, `Becerril2024`, `Carrion2024`, `LaOlmeda2024`, `Ampudia2024`, `Palomares1`, `CalleMayor1`, `CampoGotico` | spread across staff |

Generic dictionary:

| Account | Password | Note |
|---------|----------|------|
| `noelia.s` | `Verano2024` | Sales (AS-REP) → Chain C |
| `marcos.v` | `Password123` | Finance (AS-REP) → Chain E |
| `svc_web` | `Empresa2024` | weak kerberoastable service account |
| others | `Password1`, `Qwerty123`, `Admin1234`, `Bienvenido1`, `Invierno2024`, `Primavera2024`, `Redil2024`, `Cambiame1`, `Usuario2024` | spread across staff |

> The exact login↔password mapping is produced deterministically by
> `scripts/generate_config.py`; re-run it to regenerate `data/config.json`.
> Cracking any of the AS-REP/kerberoastable ones above with the generated
> dictionary yields a real foothold into one of the five escalation chains.
