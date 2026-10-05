# Linux Deployment & Systemd Service Guide

This document details the production deployment, systemd initialization, and service monitoring of the Discord Desktop File Sender on Ubuntu Linux.

---

## Workspace Layout
Ensure the project is cloned or placed at:
`/home/swayam-sahu/Manager/`

The folder hierarchy must match the structured layout:
- `app/` (core application packages)
- `SEND_FILES/` (the sandbox where files to be shared are stored)
- `logs/` (stores SQLite audit databases and stdout dumps)
- `tests/` (unit and integration tests)
- `scripts/` (setup automation)

---

## Deployment Steps

### 1. Run Setup Automation
Ensure scripts are executable and configure the python virtual environment (which links to host dbus packages) and service templates:
```bash
chmod +x scripts/setup.sh
./scripts/setup.sh
```

### 2. Configure Settings
Create or modify the `.env` file in the root workspace directory:
```ini
DISCORD_BOT_TOKEN=your_bot_token_from_developer_portal
AUTHORIZED_USERS=your_discord_numeric_id_here
SEND_FILES_PATH=~/SEND_FILES
LOG_LEVEL=INFO
LARGE_FILE_STRATEGY=split
DISCORD_GUILD_ID=your_optional_test_server_id
```

---

## Systemd User Service Setup
Running the bot as a systemd user-mode service enables it to run under your user profile session, giving it direct access to active DBus desktop locks.

### Enable User Service
```bash
# Enable the service to run on startup and start it now
systemctl --user enable --now filesender.service
```

### Check Service Status
To verify the daemon is executing correctly:
```bash
systemctl --user status filesender.service
```

### Restart Service
```bash
systemctl --user restart filesender.service
```

### Stop Service
```bash
systemctl --user stop filesender.service
```

---

## Logs and Auditing

### Live Journal Logs
Stream output logs using journalctl:
```bash
journalctl --user -u filesender.service -f -n 50
```

### Database Audits
Run SQL queries on the sqlite database to audit interactions:
```bash
sqlite3 /home/swayam-sahu/Manager/logs/audit.db "SELECT * FROM audit_logs ORDER BY id DESC LIMIT 10;"
```
Values will show:
- Discord User ID
- Discord Username
- Command string
- Name of file fetched
- Success (1/0)
- Reason (if denied or failed)
