# Security Architecture & Code Review

This document describes the Zero-Trust security layers applied to the Discord Desktop File Sender system.

---

## 1. User Authentication Gate
- **Mechanism:** The system parses a pre-configured, comma-separated list of approved Discord user IDs (`AUTHORIZED_USERS`) from the `.env` file into a python `set[int]`.
- **Validation:** Every interaction is processed through a wrapper that validates `interaction.user.id in config.AUTHORIZED_USERS`.
- **Zero-Trust policy:** All unlisted users receive a silent `Access Denied` or explicit error message. No database details or host file structures are ever leaked to unauthorized callers.

---

## 2. Desktop Lock Detection (Gnome, KDE, Cinnamon, MATE, XFCE)
- **Problem:** If a physical computer is locked, an external mobile user should not be able to retrieve active screen contents or file updates, preventing unauthorized remote access in case of device theft.
- **Solution:** A priority-based multi-desktop detector queries dbus and logind:
  - If GNOME/KDE screensaver interface properties (`org.gnome.ScreenSaver.GetActive`) return `True`, commands are blocked.
  - Falls back to querying `systemd-logind` session properties (checking `LockedHint` and session type state).
  - **Zero-Trust policy:** If any single detector claims the desktop is locked, the bot blocks the command and raises a `Desktop Locked` exception.

---

## 3. Path Traversal & Sandbox Validation
- **Problem:** Attackers could try to pass relative path markers (e.g. `../../etc/passwd` or `/var/log/syslog`) to read files outside the designated sharing folder.
- **Solution:** `validate_path(target_path)` implements a multi-step check:
  1. Blocks null bytes (`\x00`) to prevent extension truncation attacks.
  2. Resolves both the root folder (`~/SEND_FILES`) and requested path using python's `os.path.realpath` to resolve symbolic links.
  3. Verifies that the resolved absolute path starts exactly with the root folder absolute path:
     ```python
     common = os.path.commonpath([base_canonical, target_canonical])
     return common == base_canonical
     ```
  4. If a symbolic link inside the sandbox points to a file outside the sandbox, the canonical path resolves outside the root, and the check returns `False` immediately.

---

## 4. Rate Limiting Throttling
- **Command Limiter:** Prevents API spamming by limiting the number of slash commands to a configurable limit (default: 20/min per user) using a sliding-window algorithm.
- **Transfer Limiter:** Restricts large file retrieval actions (default: 10/min) to prevent network resource starvation.

---

## 5. Audit logs DB
- All successful and blocked command operations are written immediately to `logs/audit.db` using a thread-safe SQLite connector.
- Log attributes record: Timestamp, Caller ID, Username, Command name, Target file name, Success indicator, and Failure explanation.
- This database is stored locally on the host system and is never uploaded.
