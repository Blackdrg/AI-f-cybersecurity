# TODO: Implement Docker Daemon Check in POC Script

- [x] Modify `scripts/run_poc.sh` to check Docker daemon status using `docker ps` before running docker-compose.
- [x] Add OS detection and platform-specific instructions if daemon is not running (Windows: open Docker Desktop; Linux: start Docker service).
- [x] Exit script with error if daemon is not running, preventing docker-compose execution.
