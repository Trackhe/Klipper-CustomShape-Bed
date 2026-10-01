# Klipper Keepout Zone

Klipper-Extra, das **feste No-Go-Zonen** (z. B. AWD-Motorhalter) erzwingt: Jeder G-Code-Move, der in eine Zone **endet oder sie durchquert**, wird mit Fehler abgebrochen — sichtbar im Mainsail/Fluidd **Update Manager** wie andere Community-Plugins.

## Use case

500×500‑mm‑Bett, vorne links und rechts je ~50×50 mm blockiert. Statt Y global auf 450 zu kürzen, bleiben 500×500 Travel-Limits, und nur die Ecken sind gesperrt.

```
Y=500  ┌──────────────────────────────┐
       │                              │
       │         nutzbar              │
       │                              │
Y=50   │                              │
Y=0    └──■──────────────────────■────┘
       X=0 50                  450 500
```

## Installation (Mainsail / Moonraker Update Manager)

Mainsail hat keinen App-Store: Plugins erscheinen unter **Machine → Update Manager**, sobald sie in `moonraker.conf` stehen und das Extra in Klipper verlinkt ist. Genau so wie z. B. `led_effect` oder Cartographer.

### 1. Klonen & Install-Skript

SSH auf den Pi / Host:

```bash
cd ~
git clone https://github.com/Trackhe/Klipper-CustomShape-Bed.git
cd Klipper-CustomShape-Bed
./install.sh
```

Das Skript:

- verlinkt `src/keepout_zone.py` → `~/klipper/klippy/extras/keepout_zone.py`
- trägt `[update_manager keepout_zone]` in `moonraker.conf` ein
- startet Klipper (und Moonraker bei neuem Updater-Eintrag) neu

Optionen bei abweichenden Pfaden:

```bash
./install.sh -k ~/klipper -s klipper -c ~/printer_data/config
```

Deinstallieren:

```bash
./install.sh -u
```

### 2. Config einbinden

```bash
cp ~/Klipper-CustomShape-Bed/config/keepout_zone.cfg.example \
   ~/printer_data/config/keepout_zone.cfg
```

In `printer.cfg`:

```ini
[include keepout_zone.cfg]
```

Zonen/Margin anpassen, dann in Mainsail **Save & Restart**.

### 3. Update Manager prüfen

Unter **Machine → Update Manager** sollte **keepout_zone** erscheinen. Updates = Pull dieses Repos + Klipper-Neustart (`managed_services: klipper`).

Manueller `moonraker.conf`-Block (falls du ohne Skript arbeitest): siehe [`file_templates/moonraker_update.txt`](file_templates/moonraker_update.txt) — **`path:`** auf dein Clone-Verzeichnis setzen.

---

## Konfiguration

```ini
[keepout_zone]
enabled: True
margin: 2.0
# z_max: 30          # optional: nur unterhalb dieser Z-Höhe sperren

zone_1_name: front_left
zone_1_min: 0, 0
zone_1_max: 50, 50

zone_2_name: front_right
zone_2_min: 450, 0
zone_2_max: 500, 50
```

| Option | Bedeutung |
|--------|-----------|
| `margin` | Zusätzlicher Rand um jede Zone (mm) |
| `z_max` | Wenn gesetzt: Keepout nur bei `Z ≤ z_max` (Kopf kann höher darüber) |
| `check_toolhead_moves` | Auch Mesh/Probe/Beacon über `toolhead.move` prüfen (Default: True) |
| `zone_N_min` / `zone_N_max` | Rechteck-Ecken in **Maschinen-/Düsen-XY** |
| `zone_N_name` | Optionaler Name für Logs/Status |

Bis zu 99 Zonen (`zone_1_…` … `zone_99_…`).

### G-Code-Befehle

| Befehl | Funktion |
|--------|----------|
| `KEEPOUT_ZONE_STATUS` | Zonen + effektive Rechtecke (inkl. Margin) |
| `KEEPOUT_ZONE ENABLE=0` | Soft-aus (nur Recovery / Diagnose) |
| `KEEPOUT_ZONE ENABLE=1` | Wieder aktiv |

---

## Was geprüft wird — und was nicht

**Geprüft (zwei Lagen):**

1. **G-Code-Transform** — normale `G0`/`G1` (Druck, Macros, UI)  
2. **`toolhead.move` / `toolhead.drip_move`** — damit auch **Bed Mesh, Probe, Beacon**, alles was über `manual_move` läuft  

Ziel **und** Strecke gegen jedes Keepout-Rechteck. Ohne XY-Homing greift der Toolhead-Guard noch nicht (Position unzuverlässig).

| Option | Default | Bedeutung |
|--------|---------|-----------|
| `check_toolhead_moves` | `True` | Mesh/Probe/Beacon mit absichern |

**Weiterhin nicht abgedeckt:**

| Pfad | Hinweis |
|------|---------|
| `FORCE_MOVE` / reine Stepper-Moves | Low-Level, absichtlich |
| `SET_GCODE_OFFSET` | G-Code-Lage vs. Toolhead-Lage kann abweichen — physische Halter = Toolhead-Koordinaten |

Ergänzend empfohlen:

- Orca: Bed 500×500 + **Excluded bed area** für beide Ecken  
- `[bed_mesh]` `mesh_min`/`mesh_max` und ggf. `faulty_region_*` außerhalb der Halter  
- `[safe_z_home]` in die Bettmitte  

---

## Beispiel-Bed-Mesh (Skizze)

```ini
[bed_mesh]
# Werte an Probe-Offset anpassen — nicht blind kopieren
mesh_min: 25, 60
mesh_max: 475, 475
```

`position_min`/`position_max` der Achsen können wieder den vollen Hub (z. B. 0…500) nutzen.

---

## Orca Slicer

1. Printable space: **500 × 500**, Origin = Maschinen-`(0,0)`  
2. **Excluded bed area** für beide 50×50 (gern + gleicher Margin wie im Extra)  
3. Kein separates 450‑mm‑Profil mehr nötig  

---

## Entwicklung / Tests

Geometrie ohne Klipper:

```bash
python3 tests/test_geometry.py -v
```

Repo-Layout:

```
src/keepout_zone.py              # Klipper-Extra
install.sh                       # Symlink + moonraker.conf
file_templates/moonraker_update.txt
config/keepout_zone.cfg.example
tests/test_geometry.py
```

---

## Lizenz

GNU GPLv3 — siehe [LICENSE](LICENSE).
