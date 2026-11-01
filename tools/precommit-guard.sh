#!/usr/bin/env bash
# Blocks a commit that stages something that should not be public.
#
# Installed as .git/hooks/pre-commit by tools/install-hooks.sh. Versioned here
# so the rules are reviewable and travel with the repo.
#
# Deliberate override:  git commit --no-verify
#
# Written after a personal finance note sat in this public repo for a month.
# The lesson was not "be more careful" - it was that nothing checked.
set -uo pipefail

STAGED=$(git diff --cached --name-only --diff-filter=ACMR)
[ -z "$STAGED" ] && exit 0
ADDED=$(git diff --cached -U0 --diff-filter=ACMR | grep '^+' | grep -v '^+++' || true)
FAIL=0

deny_path() {            # deny_path <extended-regex> <why>
  local hits
  hits=$(printf '%s\n' "$STAGED" | grep -E -- "$1" || true)
  if [ -n "$hits" ]; then
    echo "BLOCKED  $2"
    printf '%s\n' "$hits" | sed 's/^/         /'
    FAIL=1
  fi
}

deny_content() {         # deny_content <extended-regex> <why>
  [ -z "$ADDED" ] && return 0
  local hits
  hits=$(printf '%s\n' "$ADDED" | grep -E -- "$1" | head -3 || true)
  if [ -n "$hits" ]; then
    echo "BLOCKED  $2"
    printf '%s\n' "$hits" | cut -c1-108 | sed 's/^/         /'
    FAIL=1
  fi
}

# ---- paths that must never be committed ----------------------------------
deny_path '^Claude outputs/'            "personal notes folder"
deny_path 'revenue-ladder'              "personal income and bills"
deny_path '(^|/)\.env$'                 "environment file with real values"
deny_path 'prospects.*\.csv$'           "prospect list with third-party contact details"
deny_path '^docs/referral-'             "consulting pipeline, belongs in a private repo"
deny_path '(referral_tracker|access_audit)\.py$' "consulting tooling, belongs in a private repo"
deny_path '^data/raw/real/'             "four other clubs' source documents"
deny_path 'records-real\.jsonl$'        "records built from those documents"
deny_path 'handbook-text\.txt$'         "full text of those documents"
deny_path '^out/judge.*\.csv$'          "model answers quoting those documents"
deny_path '(findings-audit|refuse-sweep|judge-report-gated|judge-report-v2-gated)\.md$' \
                                        "quotes those documents verbatim"

# ---- content that must never be committed --------------------------------
deny_content '[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.(com|org|net|edu|io)' "an email address"
deny_content '\(?[0-9]{3}\)?[ .-][0-9]{3}[ .-][0-9]{4}' "something shaped like a phone number"
deny_content '-----BEGIN [A-Z ]*PRIVATE KEY'            "a private key"
deny_content '(sk-[A-Za-z0-9]{20,}|gh[pousr]_[A-Za-z0-9]{20,}|AKIA[0-9A-Z]{16})' \
                                                        "something shaped like an API key or token"

if [ "$FAIL" -ne 0 ]; then
  cat <<'MSG'

Nothing was committed. Either unstage it:

    git restore --staged <file>

or, if this really is meant to be public, commit deliberately:

    git commit --no-verify

MSG
  exit 1
fi
exit 0
