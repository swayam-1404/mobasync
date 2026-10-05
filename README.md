# Desktop File Sender

A secure, enterprise-grade background service for Ubuntu desktop that lets pre-authorized Telegram users remotely search, list, and retrieve files from a dedicated folder (`~/SEND_FILES`) using zero-trust security checks.

---

## Key Features & Security Gates

This background daemon enforces a strict **Zero-Trust Security Model** for every operation:
1. **Telegram Caller Authentication:** Only requests from Telegram user IDs explicitly listed in the `.env` configuration file are processed.
2. **Desktop Session Lock Enforcement:** A modular multi-desktop lock detection system (supporting GNOME, KDE, XFCE, Cinnamon, and MATE) queries DBus and systemd-logind. If the desktop session is locked, all operations are rejected.
3. **Sandbox Path Validation:** Strict canonical path validation prevents directory traversal (e.g., `..`), symlink escapes, and null-byte injection. File access is locked entirely inside `~/SEND_FILES`.
4. **Command & Transfer Throttling:** Built-in sliding-window rate limiters prevent command spam and file-transfer abuse.
5. **Persistent Audit DB:** Every bot command interaction (caller, command, target file, status, failure reasons) and monitored directory file event is logged into a thread-safe SQLite database and a rotating log file inside the `logs/` folder.
6. **Large File Management:** Automatically handles zipping folders and splitting files exceeding Telegram's 50MB upload limit into smaller parts, re-assembling transparently.

---

## Project Architecture

```text
Manager/
├── app/
│   ├── bot/
│   │   └── telegram_bot.py        # Asynchronous command and transfer handlers
│   ├── config/
│   │   └── config.py              # Configuration manager for .env parsing
│   ├── database/
│   │   └── db_manager.py          # SQLite thread-safe audit logging
│   ├── security/
│   │   ├── lock_detector.py       # Desktop lock state coordinators
│   │   ├── rate_limiter.py        # Command and file-transfer rate limiters
│   │   └── validator.py           # Path validation and user authentication
│   ├── services/
│   │   ├── folder_monitor.py      # Watchdog folder change tracker
│   │   └── large_file_handler.py  # Archive creation and file splitting logic
│   └── utilities/
│       └── system_info.py         # System storage space and connectivity checks
├── logs/                          # Directory containing SQLite audit database and raw app.log
├── scripts/
│   └── setup.sh                   # Automates environment creation and service installation
├── tests/
│   ├── test_lock.py               # Unit tests for the lock detector coordinator
│   └── test_security.py           # Unit tests for path traversal, auth, and rate limits
├── .env.example                   # Template configuration file
├── filesender.service             # systemd user service template
├── requirements.txt               # PIP dependencies
├── main.py                        # Service daemon entry point
└── README.md                      # Documentation
```

---

## Deployment & Installation Guide

### Prerequisites
- **OS:** Ubuntu Desktop 22.04 LTS, 24.04 LTS, or 26.04 LTS (resolute)
- **Python:** Python 3.12+ (tested with Python 3.14)
- **DBus:** Desktop system DBus and Session DBus access enabled

### Step 1: Clone or Place the Workspace
Ensure the codebase is placed in `/home/swayam-sahu/Manager/`.

### Step 2: Setup the Telegram Bot
1. Open Telegram and search for `@BotFather`.
2. Send `/newbot` and follow the instructions to create a bot.
3. Save the **HTTP API Token** provided (e.g., `123456789:ABCdefGhIJK...`).
4. Find your numeric Telegram User ID by sending a message to `@userinfobot` or `@MissRose_bot` on Telegram.

### Step 3: Run the Setup Script
Make the script executable and run it to set up directory structures, a python virtual environment (utilizing `--system-site-packages` to link system DBus libraries), and systemd service templates:
```bash
chmod +x scripts/setup.sh
./scripts/setup.sh
```

### Step 4: Configure the Environment variables
Open the newly created `.env` file inside `/home/swayam-sahu/Manager/` and fill in your details:
```ini
BOT_TOKEN=your_telegram_bot_token_here
AUTHORIZED_USERS=your_telegram_id_here
SEND_FILES_PATH=~/SEND_FILES
LOG_LEVEL=INFO
RATE_LIMIT_COMMANDS_PER_MIN=20
RATE_LIMIT_TRANSFERS_PER_MIN=10
```

### Step 5: Start & Enable the systemd User Service
Run the service as a user-level service daemon. This allows it to run within your active user login context and safely access the active DBus graphical session:
```bash
# Enable the service to start on user login and start it now
systemctl --user enable --now filesender.service
```

---

## Managing and Monitoring the Service

### Check Service Status
```bash
systemctl --user status filesender.service
```

### View Application Logs
```bash
journalctl --user -u filesender.service -n 50 -f
```
Or directly read the logs from the workspace directory:
```bash
tail -f /home/swayam-sahu/Manager/logs/app.log
```

### Querying the Audit Database
The application logs all requests and system file change events to a SQLite database. You can query it using sqlite3 CLI:
```bash
sqlite3 /home/swayam-sahu/Manager/logs/audit.db "SELECT * FROM audit_logs ORDER BY id DESC LIMIT 10;"
```

---

## Testing Strategy

To verify the security boundaries and lock checks, automated tests are located inside the `tests/` folder.

Run the unit tests:
```bash
./venv/bin/python3 -m unittest discover -s tests
```

---

## Troubleshooting

### DBus ModuleNotFoundError inside virtual environment
If you experience `ModuleNotFoundError: No module named 'dbus'` or similar, ensure your virtual environment was created with access to system packages:
```bash
python3 -m venv --system-site-packages venv
```
And re-install pip requirements. The `scripts/setup.sh` script does this automatically.

### Service returns "Desktop Locked. Operation Denied." when unlocked
If the system is running Wayland or custom displays, systemd-logind might not register screensaver changes instantly. Ensure the `DBUS_SESSION_BUS_ADDRESS` matches your active session. You can inspect it by running:
```bash
echo $DBUS_SESSION_BUS_ADDRESS
```
Make sure this value aligns with the environment variable set in `filesender.service`. The setup script sets `unix:path=/run/user/1000/bus` which is standard for UID `1000`.

---

## Future Extensions (Refactoring Ready)
The system is built on modular SOLID design patterns and is fully prepared for future extensions:
- **Bi-directional Transfers:** Add a custom `MessageHandler(filters.Document, upload_handler)` in `telegram_bot.py` to allow uploading files from Telegram directly into `~/SEND_FILES`.
- **Desktop Notifications:** Integrate python bindings for `notify2` or DBus `org.freedesktop.Notifications` to display popup alerts on the host system when files are retrieved.
- **REST API / Web Panel:** Integrate a lightweight `fastapi` service running in a separate thread alongside the Telegram loop to expose a local web interface.
