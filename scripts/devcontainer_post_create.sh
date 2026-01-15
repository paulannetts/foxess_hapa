#! /bin/bash
# Script to run when the container starts under postCreateCommand

set -Eeuo pipefail

if [[ ! -d '/workspaces/foxess_hapa/.git' ]]; then
    printf "\nBootstrapping git repository (foxess_hapa/master), using SSH and mounted creds...\n"
    sudo chown -R vscode /workspaces

    # Verify SSH agent is accessible
    if ! ssh-add -l &>/dev/null; then
        echo "Error: SSH agent not accessible. Check SSH_AUTH_SOCK and socket permissions."
        echo "SSH_AUTH_SOCK=$SSH_AUTH_SOCK"
        ls -la "$SSH_AUTH_SOCK" 2>&1 || echo "Socket does not exist"
        exit 1
    fi
    echo "SSH agent OK: $(ssh-add -l | head -1)"

    # Add GitHub's SSH host key to known_hosts to avoid interactive prompt
    mkdir -p ~/.ssh
    ssh-keyscan -t ed25519 github.com >> ~/.ssh/known_hosts 2>/dev/null

    cd /workspaces
    git clone git@github.com:paulannetts/foxess_hapa.git foxess_hapa

    /workspaces/foxess_hapa/scripts/setup
fi

