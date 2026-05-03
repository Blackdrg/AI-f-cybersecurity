#!/bin/bash
# Simple Redis cluster init for CI (3 nodes: localhost:6379,6380,6381)

set -e

docker exec redis-node1 redis-cli --cluster create \
  localhost:6379 localhost:6380 localhost:6381 \
  --cluster-replicas 1 --cluster-yes

echo "Redis cluster initialized"
redis-cli -h localhost -p 6379 cluster info
