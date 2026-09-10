# Airthings Corentium Home 2 integration

This repository contains a Home Assistant custom integration in
`custom_components/airthings_corentium`. It uses Home Assistant's Bluetooth
manager and the `airthings-ble-corentium` package; it does not open an
independent Bluetooth scanner.

## Install

### HACS custom repository

1. In HACS, add `https://github.com/madun1999/airthings-ble` as an Integration
   custom repository.
2. Install **Airthings Corentium Home 2**.
3. Restart Home Assistant.
4. Add the integration from **Settings > Devices & services**. Select a
   discovered device or enter its Bluetooth address.

Do not configure the same Corentium in the official Airthings BLE integration.
Two integrations or the Airthings mobile app can contend for its BLE connection.

## Operation

The integration polls every five minutes by default. Home Assistant marks its
entities unavailable after a failed coordinator update and retries on the next
interval. A successful update restores them without reloading the integration.

Download diagnostics from the integration entry when reporting a problem. The
diagnostics redact the Bluetooth address and serial number and include the last
poll result, duration, firmware, and fields received.

## Suggested dashboard

Use a statistics graph for sustained exposure rather than reacting to one
reading:

```yaml
type: statistics-graph
title: Corentium radon
entities:
  - sensor.radon_24_hour_average
  - sensor.radon_7_day_average
stat_types:
  - mean
  - min
  - max
days_to_show: 30
chart_type: line
```

Entity IDs may differ if they were renamed in Home Assistant. Prefer alerts
based on the 24-hour average remaining above the threshold for several hours;
short radon fluctuations are not an actionable exposure signal.

## History safety

Raven history endpoint reads appear to consume or advance device history. This
integration deliberately does not read history automatically. Before a live
history importer is added, it must durably save every raw response before the
next request, serialize access with normal polling, resume after interruption,
and establish an unambiguous end-of-history signal. Do not experiment while the
mobile app or another integration is connected.
