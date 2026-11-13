#!/bin/bash
# Double-click this on a Mac: it opens Terminal and starts openFerment.
# The same as running `bash start.sh` in this folder.
cd "$(dirname "$0")" || exit 1
bash start.sh
status=$?
printf '\nPress Enter to close this window. '
read -r _
exit $status
