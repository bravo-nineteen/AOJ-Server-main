# Team-Terminals

Flutter tactical tablet UI for AOJ Command OS field operations.

## Features

- Team-themed desktop interface (Task Force Onyx / Black Talon)
- Admin PIN gate and first-run setup
- Local data persistence for roster, devices, comms, and game files
- AOJ backend sync support with configurable host and port
- Server status visibility and manual sync controls from admin panel

## Run Locally

```bash
cd Team-Terminals-main
flutter pub get
flutter run
```

## Build APK

Use the repository-level CLI wrapper:

```bash
./scripts/team_terminals_apk_cli.sh build --release
```

Common variants:

```bash
./scripts/team_terminals_apk_cli.sh build --debug
./scripts/team_terminals_apk_cli.sh build --split-per-abi
./scripts/team_terminals_apk_cli.sh locate
```

By default, generated APKs are copied into:

`outputs/team-terminals-apk/<version_timestamp>/`
