#!/usr/bin/env bash
# Exit immediately if a command exits with a non-zero status
set -e

PROJECT_DIR="/home/swayam-sahu/Manager"
SEND_FILES_DIR="$HOME/SEND_FILES"
SYSTEMD_USER_DIR="$HOME/.config/systemd/user"

echo "=================================================="
echo "🚀 Desktop File Sender - Setup & Deployment"
echo "=================================================="

# 1. Create SEND_FILES directory
echo "📁 Creating SEND_FILES directory at: $SEND_FILES_DIR"
mkdir -p "$SEND_FILES_DIR"

# 2. Check Python installation
echo "🐍 Verifying Python 3 installation..."
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 is not installed. Please install Python 3.12+."
    exit 1
fi

# 3. Create virtual environment if it doesn't exist
if [ ! -d "$PROJECT_DIR/venv" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv --system-site-packages "$PROJECT_DIR/venv"
fi

# 4. Install dependencies
echo "📥 Installing/Updating dependencies from requirements.txt..."
"$PROJECT_DIR/venv/bin/pip" install --upgrade pip
"$PROJECT_DIR/venv/bin/pip" install -r "$PROJECT_DIR/requirements.txt"

# 5. Create .env file if it doesn't exist
if [ ! -f "$PROJECT_DIR/.env" ]; then
    echo "📝 Creating .env from template..."
    cp "$PROJECT_DIR/.env.example" "$PROJECT_DIR/.env"
    echo "⚠️  Created .env file! Please edit it and fill in DISCORD_BOT_TOKEN and AUTHORIZED_USERS before starting the service."
else
    echo "✅ .env file already exists."
fi

# 6. Configure systemd user service
echo "⚙️  Configuring systemd user service..."
mkdir -p "$SYSTEMD_USER_DIR"

# Copy service file
cp "$PROJECT_DIR/filesender.service" "$SYSTEMD_USER_DIR/filesender.service"

# Reload systemd user daemon
systemctl --user daemon-reload

echo "=================================================="
echo "✅ Setup Completed Successfully!"
echo "=================================================="
echo "Next Steps:"
echo "1. Open $PROJECT_DIR/.env and set your DISCORD_BOT_TOKEN and AUTHORIZED_USERS."
echo "2. Run this command to start the background service:"
echo "   systemctl --user enable --now filesender.service"
echo "3. Monitor service status and logs:"
echo "   systemctl --user status filesender.service"
echo "   journalctl --user -u filesender.service -f"
echo "=================================================="
