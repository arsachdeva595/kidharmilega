#!/bin/sh
# Copies the database, profiles and login out of the Docker volume into ./backups/ (run from this folder; add to cron)
set -e
mkdir -p backups
docker compose exec -T app sh -c 'cd /data && tar czf - buyer_finder.db profiles auth.json 2>/dev/null' > "backups/buyer-finder-$(date +%F).tgz"
ls -1t backups/*.tgz | tail -n +31 | xargs -r rm --
echo "Saved backups/buyer-finder-$(date +%F).tgz"
