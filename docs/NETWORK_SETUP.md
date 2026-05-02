# AOJ Command OS Network Setup

## Goal

This guide describes a practical field network for AOJ Command OS at an airsoft site using:
- One Raspberry Pi
- One local router or access point
- Several tablets or phones for staff
- LoRa-enabled props in the field

The system is designed to run without internet access.

## Recommended Topology

```text
Staff Tablets / Phones
        |
        | Wi-Fi
        v
   Field Router / AP
        |
        | Ethernet or Wi-Fi
        v
   Raspberry Pi

LoRa Props <---- LoRa Radio Link ----> Raspberry Pi LoRa Service
```

## Roles of Each Network Layer

### Wi-Fi / LAN

Use the router LAN for:
- Frontend access from staff browsers
- REST API traffic between frontend and backend
- WebSocket live updates
- SSH maintenance access to the Raspberry Pi

### LoRa

Use LoRa for:
- Prop commands
- Prop acknowledgements
- Low-bandwidth prop status traffic

Do not depend on Wi-Fi coverage for prop-to-command connectivity if the field is large. That is the job of the LoRa layer.

## Recommended IP Plan

Use a private subnet dedicated to the event. Example:

- Router LAN IP: `192.168.50.1`
- Raspberry Pi static IP: `192.168.50.10`
- DHCP pool for tablets: `192.168.50.100` to `192.168.50.199`

Why static IP on the Pi:
- Staff need a stable address for the dashboard
- Systemd services and printed field instructions can point to one known host

## Raspberry Pi Network Configuration

Recommended approach:
- Reserve a DHCP lease for the Pi in the router
- Or set a static IP on the Pi if the router is basic or unmanaged

Operational recommendation:
- Prefer Ethernet from Pi to router when possible for stability
- If Wi-Fi must be used for the Pi, ensure the control room location has strong signal and low interference

## Ports Used by AOJ Command OS

Current defaults:
- Backend API: `8000`
- Frontend preview or static serving: `4173`
- Frontend dev server during development: `5173`

Practical access examples:
- Frontend: `http://192.168.50.10:4173`
- Backend health: `http://192.168.50.10:8000/api/health`
- WebSocket: `ws://192.168.50.10:8000/ws/live`

## Browser Access Pattern

Operator tablets should connect to the frontend URL, not directly to API routes.

Typical operator workflow:
1. Join the event Wi-Fi.
2. Open the AOJ Command OS frontend in the browser.
3. Keep the page pinned or bookmarked on the tablet home screen.

## CORS Behavior

The backend currently allows LAN-oriented origins matching:
- `localhost`
- `127.0.0.1`
- `192.168.x.x`
- `10.x.x.x`
- `172.16.x.x` through `172.31.x.x`

This supports common private network ranges used on field routers.

## Router Setup Checklist

Recommended router settings:
- Use a dedicated SSID for event staff devices
- Set WPA2 or WPA3 security
- Disable captive portal behavior
- Keep client isolation off if tablets must reach the Raspberry Pi directly
- Enable DHCP for staff tablets
- Reserve the Raspberry Pi address

Avoid:
- Guest mode with isolation enabled
- Mesh roaming behavior that causes slow local DNS or client discovery issues
- Internet-dependent captive portal pages

## DNS and Naming

Best option:
- Use the Pi IP directly in field docs and bookmarks

Optional option:
- If your router supports local DNS, create a hostname such as `aoj.local` or `command.local`

Use IP-first documentation even if hostname works. It reduces confusion during field troubleshooting.

## Reliability Practices for Game Day

- Reboot the router and Raspberry Pi before the event starts
- Connect the Raspberry Pi to stable power, ideally with a UPS or a high-quality battery pack if mains power is unreliable
- Keep the router and Pi in a marshal or admin zone, not in the active play area
- Test frontend, backend, and websocket connectivity from at least two tablets before the first briefing
- Verify the Pi can still be reached if internet WAN is unplugged

## LoRa Placement Notes

For the future hardware-backed LoRa service:
- Mount the LoRa antenna clear of metal obstructions
- Keep the Pi and radio module elevated where practical
- Test dead zones at the farthest props before players arrive
- Separate router and LoRa antennas if RF interference is suspected

## Troubleshooting

### Tablets can join Wi-Fi but cannot load AOJ

Check:
- Pi IP address is correct
- Backend service is listening on `0.0.0.0:8000`
- Frontend service is listening on `0.0.0.0:4173`
- Router client isolation is disabled

### Frontend loads but live updates do not work

Check:
- WebSocket route `/ws/live` is reachable
- Port `8000` is not blocked by firewall
- Backend service is running

### Some tablets work and others do not

Check:
- Browser cache on the failing tablets
- Weak Wi-Fi in that part of the staging area
- Incorrect manual URL entry

### Props are not responding but Wi-Fi dashboard is healthy

Check:
- LoRa service mode and pending ACK count in System Monitor
- Radio hardware power and wiring once hardware integration exists
- Prop battery and physical placement

## Minimum Pre-Game Network Test

Before the first round:

1. Ping the Raspberry Pi from a laptop on the event Wi-Fi.
2. Open the frontend URL from two separate tablets.
3. Load `/api/health` in a browser.
4. Confirm the frontend shows the system as connected.
5. If LoRa hardware is in use later, send one prop status request to a test prop.