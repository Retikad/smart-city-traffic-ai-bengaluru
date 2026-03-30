# Makefile for common Docker workflows

.PHONY: docker-up docker-down docker-build docker-logs docker-bash-backend seed-db
.PHONY: dev-up dev-down dev-logs

docker-up:
	docker-compose up --build -d

docker-down:
	docker-compose down

docker-build:
	docker-compose build --no-cache

docker-logs:
	docker-compose logs -f --tail=200

# Open a shell in the backend container
docker-bash-backend:
	@container=$$(docker-compose ps -q backend) && \
	if [ -n "$$container" ]; then docker exec -it $$container /bin/sh; else echo "Backend not running"; fi

# Copy local DB into the backend volume (be careful: will overwrite volume DB)
seed-db:
	@echo "Seeding DB into volume (will overwrite existing DB in volume)" && \
	if [ -f ./bengaluru_traffic.db ]; then \
	  vol=$$(docker volume ls -q | grep traffic_congestion_backend_data || true); \
	  if [ -z "$$vol" ]; then docker volume create traffic_congestion_backend_data; vol=$$(docker volume ls -q | grep traffic_congestion_backend_data); fi; \
	  tmp=$$(mktemp -d); cp ./bengaluru_traffic.db $$tmp/ && \
	  docker run --rm -v $$vol:/data -v $$tmp:/tmp busybox sh -c "cp /tmp/bengaluru_traffic.db /data/bengaluru_traffic.db" && \
	  echo "Seeded DB into volume"; \
	else \
	  echo "No local bengaluru_traffic.db found in project root"; \
	fi

dev-up:
	docker-compose up --build -d backend-dev frontend-dev

dev-down:
	docker-compose down

dev-logs:
	docker-compose logs -f backend-dev frontend-dev --tail=200
