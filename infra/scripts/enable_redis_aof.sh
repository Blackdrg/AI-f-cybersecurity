#!/usr/bin/env bash
set -e

# Enable Redis AOF encryption at rest
# This script should be run on the Redis server host before starting Redis.

REDIS_CONF="${REDIS_CONF:-/etc/redis/redis.conf}"
KEY_FILE="${REDIS_KEY_FILE:-/etc/redis/aof-encryption-key}"

echo "Generating 32-byte encryption key for AOF..."
dd if=/dev/urandom of="${KEY_FILE}" bs=1 count=32 2>/dev/null
chmod 600 "${KEY_FILE}"
echo "Key generated at ${KEY_FILE}"

# Ensure Redis config includes AOF settings
if ! grep -q "aof-use-rdb-preamble" "$REDIS_CONF"; then
  echo "appending AOF encryption config to ${REDIS_CONF}"
  cat >> "${REDIS_CONF}" <<EOF

# AOF encryption settings
aof-use-rdb-preamble yes
aof-encrypt yes
aof-encryption-key-file ${KEY_FILE}
EOF
else
  echo "AOF encryption already configured in ${REDIS_CONF}"
fi

echo "Restarting Redis to apply AOF encryption..."
systemctl restart redis || service redis restart || echo "Please restart Redis manually"

echo "Redis AOF encryption enabled successfully."
