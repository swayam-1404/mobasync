# Upgrade & Future Roadmap

This document outlines architectural preparation and implementation strategies for future features on the Discord Desktop File Sender.

---

## Phase 1: Rich UI Interactions (Buttons & Modals)
- **Modals for File Search:** Instead of simple command line parameters, launch a Discord Modal on `/search` to input advanced search terms (e.g. date range, size limits).
- **Direct Download/Retrieval Buttons:** In the paginated `/files` embed, add a custom button under each file item so users can download files directly by clicking the button rather than typing `/get filename`.

---

## Phase 2: Upload Files to Host PC
- **Flow:** Pre-authorized users send a document directly to the bot.
- **Security Check:** Apply same path validations, lock validations, and limit checking.
- **Code hook:** Add a listener for `on_message` to check if a message has attachments, download the attachment, and save it safely in a sub-folder `~/SEND_FILES/uploads/` after sanitizing the filename.

---

## Phase 3: Bi-directional Approval Popups
- **Flow:** If a remote user requests an extremely sensitive file, trigger a host OS popup (using python tkinter or PySide/Qt) asking the local desktop user for permission.
- **Timeout:** If the local user does not click "Approve" within 60 seconds, the transfer is automatically cancelled and denied.

---

## Phase 4: Local REST API & Web Dashboard
- **Web interface:** Add a lightweight FastAPI application running in a background python thread.
- **Operations:** The web panel allows local admins to manage `AUTHORIZED_USERS`, view live audit logs, and browse `SEND_FILES` stats via a modern browser GUI.
- **Security:** Bind the server only to the local loopback interface (`127.0.0.1`) or to the Tailscale VPN interface.

---

## Phase 5: Tailscale Integration & End-to-End Encryption
- **Tailscale Link:** Restrict the LinkStrategy download URLs exclusively to the host's Tailscale IP address (e.g. `100.x.y.z`), preventing exposure to the public internet.
- **E2E Encryption:** Encrypt generated file chunks or zip archives using PyCryptodome (AES-256) with a pre-shared key stored only on the client mobile device and the host machine.
