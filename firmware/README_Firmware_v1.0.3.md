# ArduinoPDM – Firmware v1.0.3

Detta är den frysta versionen 1.0.3 av firmware för ArduinoPDM. Den är nu markerad som **release candidate (RC)**.

## ✅ Funktioner

- Styr upp till 8 reläutgångar via CAN
- Mappning mellan switchar och reläer (via `switchToRelayMap[]`)
- Direkt- och toggle-läge per relä
- Konfigurerbar via CAN:
  - ToggleMask
  - CAN-ID
  - Statusintervall
- EEPROM-lagring av konfiguration och relästatus
- CAN-statusmeddelande varje sekund (RelayMask)
- Start-ACK via CAN (`0x6A0`)
- Firmwareversion kan hämtas via kommando
- Debug-utgång via Serial (kan avaktiveras)

## 📡 CAN-meddelanden

| CAN-ID  | Funktion           | Kommentar                             |
|---------|--------------------|----------------------------------------|
| `0x650` | Status             | Skickas varje sekund (RelayMask)       |
| `0x660` | Kommandon in       | SET, SAVE, GET, osv.                   |
| `0x661` | Svar på kommandon  | Returnerar ToggleMask, CAN-ID, m.m.    |
| `0x6A0` | Start-ACK          | Skickas en gång vid uppstart           |

## 🔧 Signaldefinitioner i 0x650

- `RelayMask` (byte 0): 8-bitars bitmask för aktuella relästatusar
- `Relay1`–`Relay8`: individuella bitar tolkade från masken

## 🧱 Använda `.dbf`/`.dbc`

BUSMASTER testad med både `.dbf` (DatabaseEditor-format) och `.dbc` (bitmappade signaler per relä). Rekommenderad `.dbc` finns i `/dbc/`.

## 🛠 Mjukvaruversion

- Firmware: `v1.0.3`
- Kompilator: Arduino IDE 1.8.x / PlatformIO
- Målplattform: Arduino Nano (ATmega328P) + MCP2515 (8 MHz)

## 📦 Filer

- `ArduinoPDM_v1_0_3.ino` – källkod för firmware
- `ArduinoPDM_FinalTest.dbc` – bitmappad signalbeskrivning
- `ArduinoPDM_OnlyStatus.dbf` – enkel DBF för BUSMASTER
- `PDM_ConfigTool_0.3.4.py` – Python GUI-konfigurator (valfritt)

## 🧊 Versionsstatus

Denna version är **fryst** för release och vidareutveckling görs i `dev/1.1.0`-grenen.
Inga funktionella ändringar sker härifrån utan versionsbump.

---
© 2025 Jan Lindvall / ErRoR Engineering