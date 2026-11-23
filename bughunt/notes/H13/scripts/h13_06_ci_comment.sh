#!/bin/bash
# H13-06: the CI workflow's comment names a smoke script the tree no longer holds.
cd /home/user/openFermentUI || exit 2
grep -n 'smoke.mjs' .github/workflows/verify.yml
ls scripts/smoke.* 2>&1
grep -n 'CHROMIUM_PATH' scripts/smoke.ts
