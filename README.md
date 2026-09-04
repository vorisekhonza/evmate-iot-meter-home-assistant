# EVmate IoT Meter for Home Assistant

Experimental custom integration for the **EVmate IoT Meter** using its local HTTP endpoint:

`http://<device-ip>:8000/updateData`

## Features

- Voltage L1/L2/L3
- Current L1/L2/L3
- Active power L1/L2/L3 and total
- Power factor L1/L2/L3
- Positive/negative cumulative energy counters
- EVSE-related values when exposed by the firmware, including requested/output current, EVSE status, charging duration, session energy, charging user, SOC and raw charge mode

## Installation with HACS

1. In HACS, add this repository as a **Custom repository** of type **Integration**.
2. Install **EVmate IoT Meter**.
3. Restart Home Assistant.
4. Go to **Settings → Devices & services → Add integration**.
5. Search for **EVmate IoT Meter**.
6. Enter the IoT Meter IP address and port `8000`.

## Manual installation

Copy:

`custom_components/evmate_iot_meter`

into:

`/config/custom_components/evmate_iot_meter`

Restart Home Assistant and add the integration from **Settings → Devices & services**.

## Notes

This is an unofficial community integration and is not affiliated with EVmate.

Some EVSE fields are firmware-dependent. If a field is not returned by `/updateData`, the corresponding entity stays unavailable until the field appears.

The integration currently polls the local endpoint every 10 seconds.

## Status

Early test version. Sensor scaling and direction of positive/negative energy counters should be verified against the EVmate application on additional installations before being treated as universally valid.
