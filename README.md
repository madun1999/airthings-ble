# airthings-ble-corentium

Fork of [Airthings/airthings-ble](https://github.com/Airthings/airthings-ble)
that adds Corentium Home 2 diagnostics and Raven history payload decoding while
preserving the `airthings_ble` Python import namespace.

## Supported devices

This library supports the following Airthings devices:

- [Corentium Home 2](https://www.airthings.com/products/corentium-home-2)
- [Wave Enhance](https://www.airthings.com/wave-enhance)
- Wave Gen 1
- [Wave Mini](https://www.airthings.com/wave-mini)
- [Wave Plus](https://www.airthings.com/wave-plus)
- [Wave Radon](https://www.airthings.com/wave-radon)

## Unsupported devices
Although some other devices have BLE capabilities, they use BLE only for onboarding and configuration. It is **not** possible to fetch sensor data using this library from, for example:

-	Hub
-	[Renew](https://www.airthings.com/renew)
-	[View Plus](https://www.airthings.com/view-plus)
-	View Pollution
-	[View Radon](https://www.airthings.com/view-radon)

## Getting Started

Prerequisites:

- [Python](https://www.python.org/downloads/) with version 3.12 that is required by Home Assistant ([docs](https://developers.home-assistant.io/docs/development_environment?_highlight=python&_highlight=versi#manual-environment) or [reference](https://github.com/home-assistant/architecture/blob/master/adr/0002-minimum-supported-python-version.md))
- [Poetry](https://python-poetry.org/docs/#installation)

Install dependencies:

```bash
poetry install
```

Run tests:

```bash
poetry run pytest
```

See the [upstream wiki](https://github.com/Airthings/airthings-ble/wiki/Testing-with-Home-Assistant)
for details on testing the library with Home Assistant.

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.
