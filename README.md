# ThermoPro TP920 – Home Assistant Integration

Home Assistant integration for the **ThermoPro TP920** Bluetooth thermometer.
---

## Features

- Bluetooth Low Energy (BLE) support
- Two temperature probe sensors
- Config flow for easy setup
- User-selectable temperature unit (°C / °F)
- Configurable polling interval
- Compatible with Home Assistant Bluetooth stack
- Installable via **HACS**

> The integration does **not** modify the unit shown on the TP920 device itself.

---

## Installation

### HACS (recommended)

1. Add this repository to HACS as a **Custom Repository**
2. Install **ThermoPro TP920**
3. Restart Home Assistant
4. Add the integration via **Settings → Devices & Services**

### Manual

1. Copy `thermopro_tp920` to: config/custom_components/
2. Restart Home Assistant
3. Add **ThermoPro TP920** from **Devices & Services**

---

## Configuration

During setup you can select:
- Bluetooth address (auto-discovered when available)
- Temperature unit (°C / °F)
- Update interval (seconds)

---

## Entities

- **Probe 1** – Temperature
- **Probe 2** – Temperature

---
