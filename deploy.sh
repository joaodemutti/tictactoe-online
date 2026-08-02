#!/usr/bin/env bash
#
# Deploy the latest main to this server.
#
#   cd /opt/tictactoe && ./deploy.sh
#
# Pulls the newest code, then only reinstalls deps / runs migrations if those
# files actually changed in the pull. Fixes file permissions for the service
# user and restarts. Needs sudo for the chown/chmod/systemctl steps.

set -euo pipefail

APP_DIR="/opt/tictactoe"
SERVICE="tictactoe"
VENV="$APP_DIR/venv"

cd "$APP_DIR"

echo "==> Pulling latest code..."
BEFORE=$(git rev-parse HEAD)
git pull --ff-only
AFTER=$(git rev-parse HEAD)

if [ "$BEFORE" = "$AFTER" ]; then
    echo "    Already up to date ($AFTER)."
    CHANGED=""
else
    echo "    $BEFORE -> $AFTER"
    CHANGED=$(git diff --name-only "$BEFORE" "$AFTER")
fi

# --- Dependencies: only if requirements.txt changed ---
if echo "$CHANGED" | grep -qx 'requirements.txt'; then
    echo "==> requirements.txt changed -> installing deps..."
    # shellcheck disable=SC1091
    source "$VENV/bin/activate"
    pip install -r requirements.txt
    deactivate
else
    echo "==> requirements.txt unchanged -> skipping pip install."
fi

# --- Migrations: only if a new migration file appeared ---
if echo "$CHANGED" | grep -q '^alembic/versions/'; then
    echo "==> New migration detected -> alembic upgrade head..."
    "$VENV/bin/alembic" upgrade head
else
    echo "==> No new migrations -> skipping alembic."
fi

# --- Permissions for the service user (fastapi) to read new files ---
echo "==> Fixing permissions..."
sudo chown -R deploy:fastapi "$APP_DIR"
sudo chmod -R g+rX "$APP_DIR"
sudo chmod 640 "$APP_DIR/.env"

# --- Restart and verify ---
echo "==> Restarting $SERVICE..."
sudo systemctl restart "$SERVICE"
sudo systemctl status "$SERVICE" --no-pager
echo
echo "==> Recent logs:"
sudo journalctl -u "$SERVICE" -n 30 --no-pager

echo
echo "==> Deploy complete."
