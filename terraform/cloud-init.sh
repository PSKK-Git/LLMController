#!/bin/bash
set -euxo pipefail

# Install Docker (Oracle Linux 9)
dnf install -y git
curl -fsSL https://get.docker.com | sh
systemctl enable --now docker

# Open the app port in the OS firewall
firewall-cmd --permanent --add-port=8000/tcp || true
firewall-cmd --reload || true

# Fetch and run the app
git clone ${repo_url} /opt/llmcontroller
cd /opt/llmcontroller

cat > .env <<ENVEOF
ANTHROPIC_API_KEY=${anthropic_api_key}
ADMIN_TOKEN=${admin_token}
ENVEOF

docker compose -f docker-compose.prod.yml up -d --build
