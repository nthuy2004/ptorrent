# pTorrent Tracker Deploy

## Components
- `tracker-api`: Apache 2 + PHP 8.2 runtime serving `/register.php` and `/announce.php`.
- `tracker-db`: MySQL 8.0 database storing torrent metadata and active peer bitfields.
- `schema.sql`: Initial schema automatically loaded on database startup.

## Deploy step

1. Start Tracker and Database:
   ```bash
   docker compose -f deploy/docker-compose.yml up -d
   ```

2. Check service status:
   ```bash
   docker compose -f deploy/docker-compose.yml ps
   ```

3. Test tracker connectivity:
   ```bash
   curl http://localhost:8080/announce.php
   ```
   (Should return HTTP 400 with `missing required fields`, indicating tracker is active).

4. Configure Client to use local tracker:
   Pass `--tracker-url http://localhost:8080` when starting pTorrent:
   ```bash
   python src/client/main.py --tracker-url http://localhost:8080
   ```

5. Stop services:
   ```bash
   docker compose -f deploy/docker-compose.yml down
   ```
