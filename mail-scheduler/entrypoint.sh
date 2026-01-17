#!/bin/sh
set -e

# Default values
host="${RABBITMQ_HOST:-rabbitmq}"
port="${RABBITMQ_PORT:-5672}"

echo "Waiting for rabbitmq at $host:$port..."

# Loop until we can connect to the host and port
while ! nc -z "$host" "$port"; do
  echo "RabbitMQ is unavailable - sleeping"
  sleep 2
done

echo "RabbitMQ is up - executing command"
exec "$@"
