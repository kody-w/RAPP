#!/usr/bin/env bash
# RAPP Brainstem — one-time setup that makes `here` a recognized command
# in every future bash/zsh session on this account.
#
# Run once:
#     curl -fsSL https://kody-w.github.io/RAPP/installer/setup-here.sh | bash
#
# From then on, any new shell lets you do:
#     here
#     curl -fsSL https://kody-w.github.io/RAPP/installer/install.sh | bash
#
# Mechanism: appends a tiny function definition to ~/.bashrc and ~/.zshrc
# (whichever exist; both if both). The function exports here=1 so the
# next install one-liner reads it and triggers project-local mode.

set -e

MARKER='# >>> RAPP-here-shim'
read -r -d '' BLOCK <<'EOF' || true
# >>> RAPP-here-shim
here() {
    echo 'here = 1  (next RAPP install will be project-local)'
    export here=1
}
# <<< RAPP-here-shim
EOF

install_into() {
    local rc="$1"
    if [ ! -f "$rc" ]; then
        # Don't create an rc file if the user doesn't have one — only
        # extend the ones they already use.
        return 1
    fi
    if grep -qF "$MARKER" "$rc" 2>/dev/null; then
        echo "  ✓ here() already installed in $rc — no change made"
        return 0
    fi
    {
        echo ""
        echo "$BLOCK"
    } >> "$rc"
    echo "  ✓ here() appended to $rc"
    return 0
}

INSTALLED=0
for rc in "$HOME/.bashrc" "$HOME/.bash_profile" "$HOME/.zshrc"; do
    install_into "$rc" && INSTALLED=$((INSTALLED + 1))
done

if [ "$INSTALLED" = "0" ]; then
    # No existing rc files — write a fresh ~/.bashrc so something picks up.
    install_into "$HOME/.bashrc" || {
        cat > "$HOME/.bashrc" <<EOF
$BLOCK
EOF
        echo "  ✓ created $HOME/.bashrc with here() defined"
    }
fi

echo ""
echo "Next:"
echo "  here"
echo "  curl -fsSL https://kody-w.github.io/RAPP/installer/install.sh | bash"
echo ""
echo "(Open a new shell, or 'source ~/.bashrc' / 'source ~/.zshrc' to use here() right now.)"
