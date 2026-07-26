#!/usr/bin/env bash
set -euo pipefail

host="${1:?Missing host}"
port="${2:?Missing port}"
shift 2
cmd=("$@")

echo "Waiting for $host:$port..."

until nc -z "$host" "$port"; do
  sleep 1
done

echo "$host:$port is available, executing: ${cmd[*]}"
exec "${cmd[@]}"
