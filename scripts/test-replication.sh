#!/bin/bash

set -e

echo "=== PhishingPlatform Replication Test ==="

echo ""
echo "1. Checking service replicas..."
docker service ls | grep phishing

echo ""
echo "2. Testing Backend API load balancing..."
for i in {1..10}; do
  response=$(curl -s http://localhost/health)
  echo "Request $i: $response"
done

echo ""
echo "3. Checking RabbitMQ queues..."
curl -s -u guest:guest http://localhost:15672/api/queues | python3 -m json.tool | head -50

echo ""
echo "4. Checking database connections..."
docker exec $(docker ps -q -f name=phishing_postgres) psql -U phishing_user -d phishing_db -c "SELECT count(*) FROM pg_stat_activity WHERE datname = 'phishing_db';"

echo ""
echo "5. Running replication unit tests..."
docker exec $(docker ps -q -f name=phishing_backend-api | head -1) pytest tests/test_replication.py -v

echo ""
echo "=== Replication Test Complete ==="
