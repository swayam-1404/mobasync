# Discord Bot Setup & Configuration Guide

This guide walks you through setting up a Discord Bot, generating the OAuth2 invitation URL with correct permissions, and registering slash commands.

---

## Step 1: Create a Discord Application
1. Go to the [Discord Developer Portal](https://discord.com/developers/applications).
2. Log in with your Discord account.
3. Click the **New Application** button in the top-right corner.
4. Give your application a name (e.g., `DesktopFileSender`) and agree to the Developer Terms of Service. Click **Create**.

---

## Step 2: Configure the Bot Settings
1. On the left sidebar menu, click on **Bot**.
2. Click the **Add Bot** button if it is not already created.
3. **Bot Token:**
   - Under the bot username section, click **Reset Token** and copy the generated token.
   - **Crucial:** Save this token immediately. You will paste this as `DISCORD_BOT_TOKEN` in your `.env` file.
4. **Privileged Gateway Intents:**
   - Scroll down to the **Privileged Gateway Intents** section.
   - You only need default intents since all interactions are handled via Slash Commands. However, ensure that **Presence Intent** or **Server Members Intent** are toggled off unless required, to maintain a zero-trust profile.

---

## Step 3: OAuth2 & Permission Setup
To invite the bot to your private server, configure the OAuth2 URL Generator:
1. On the left sidebar menu, click on **OAuth2**, then select **URL Generator**.
2. Under **Scopes**, select the **bot** checkbox.
3. Once selected, a **Bot Permissions** grid will appear below. Select the following permissions:
   - **Send Messages** (to respond to commands)
   - **Attach Files** (critical for sending files)
   - **Use Slash Commands** (critical for registering commands)
4. Copy the generated URL at the bottom of the page.
5. Paste this URL into a web browser tab, select the target Discord Server where you want to deploy the bot, and click **Authorize**.

---

## Step 4: Obtain Your Discord User ID
To authorize yourself to run commands:
1. Open Discord desktop or web application.
2. Go to **User Settings** -> **Advanced**.
3. Toggle on **Developer Mode**.
4. Right-click your profile picture on the bottom-left or in a chat list, and click **Copy User ID** (a 17-to-19 digit number).
5. Open your `.env` file and set `AUTHORIZED_USERS=your_copied_id`.

---

## Step 5: Slash Command Syncing
- By default, the bot synchronizes commands globally on startup, which may take up to an hour.
- **Tip for Developers:** To make commands appear instantly in your private development server, copy the Server ID (Guild ID) by right-clicking the server icon, and add it to `.env` as `DISCORD_GUILD_ID=your_guild_id`. The bot will sync commands immediately to that server.
