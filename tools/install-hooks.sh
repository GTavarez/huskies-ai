#!/usr/bin/env bash
# Run once per clone:   bash tools/install-hooks.sh
set -euo pipefail
cd "$(git rev-parse --show-toplevel)"
mkdir -p .git/hooks
cat > .git/hooks/pre-commit <<'HOOK'
#!/usr/bin/env bash
g="$(git rev-parse --show-toplevel)/tools/precommit-guard.sh"
[ -x "$g" ] || [ -f "$g" ] || exit 0
bash "$g"
HOOK
chmod +x .git/hooks/pre-commit tools/precommit-guard.sh
echo "pre-commit guard installed. Testing it against an empty stage:"
bash tools/precommit-guard.sh && echo "  guard runs clean on an empty stage."
