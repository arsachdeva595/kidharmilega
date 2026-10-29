# Deploying Buyer Finder to your VPS

One private login, served over HTTPS at a subdomain such as `buyers.kidharmilega.in`.
Works the same on the Hostinger VPS or the Oracle Cloud server (Ubuntu 22.04/24.04).
Docker runs the app; Caddy gets and renews the HTTPS certificate on its own.

## 1. Point a subdomain at the server

At the DNS provider for kidharmilega.in, add an **A record**: name `buyers`, value = the server's public IP.
The main site on GitHub Pages is not affected.

## 2. Open ports 80 and 443

- **Hostinger:** hPanel → VPS → Firewall: allow TCP 80 and 443 (or leave the firewall off).
- **Oracle Cloud:** VCN → Security List → add ingress rules for TCP 80 and 443 from `0.0.0.0/0`. Oracle's
  Ubuntu images also block them in iptables, so on the server run:
  ```bash
  sudo iptables -I INPUT 6 -m state --state NEW -p tcp --dport 80 -j ACCEPT
  sudo iptables -I INPUT 6 -m state --state NEW -p tcp --dport 443 -j ACCEPT
  sudo netfilter-persistent save
  ```

## 3. Install Docker and get the code

```bash
curl -fsSL https://get.docker.com | sudo sh
sudo usermod -aG docker $USER && newgrp docker
git clone https://github.com/arsachdeva595/kidharmilega.git && cd kidharmilega
```
If the repo is private, clone with a GitHub personal access token or a deploy key.

## 4. Configure and start

```bash
cd buyer_finder/web
cp .env.example .env
nano .env                       # set DOMAIN=buyers.kidharmilega.in (and ANTHROPIC_API_KEY if you want)
docker compose up -d --build
docker compose run --rm app python -m buyer_finder.web set-password   # choose username + password (12+ chars)
```

Open `https://buyers.kidharmilega.in` on your phone and sign in. Use "Add to Home Screen" for an app-like icon.
You stay signed in for 30 days per device; 5 wrong passwords lock that IP out for 15 minutes.

## Everyday

| Task | Command (in `buyer_finder/web/`) |
|---|---|
| Update after a git push | `git pull && docker compose up -d --build` |
| Change password | `docker compose run --rm app python -m buyer_finder.web set-password` |
| Logs | `docker compose logs -f app` |
| Backup now | `./backup.sh` (keeps the last 30 in `backups/`) |
| Nightly backup | `crontab -e` → `30 2 * * * cd ~/kidharmilega/buyer_finder/web && ./backup.sh` |
| Use the CLI on the server | `docker compose exec app python -m buyer_finder search journals` |

Your leads, profiles and login live in the `bf-data` Docker volume, not in git. Copy `backups/` off the
server now and then (e.g. `scp`).

## Running it on your laptop instead

```bash
pip install -r buyer_finder/web/requirements.txt
python3 -m buyer_finder.web set-password
BF_INSECURE_COOKIES=1 python3 -m buyer_finder.web run      # http://localhost:8000
```
`BF_INSECURE_COOKIES=1` is only for plain-http localhost; never set it on the server.
