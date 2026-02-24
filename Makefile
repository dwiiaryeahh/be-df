.PHONY: help build up down logs shell-app health clean rebuild

help:
	@echo "DF-Backpack Docker Commands"
	@echo "============================"
	@echo "make build        - Build Docker images"
	@echo "make up           - Start services"
	@echo "make down         - Stop services"
	@echo "make restart      - Restart services"
	@echo "make logs         - View logs (app service)"
	@echo "make logs-follow  - Follow logs in real-time"
	@echo "make shell-app    - Open app container shell"
	@echo "make ps           - Show services status"
	@echo "make health       - Check app health"
	@echo "make clean        - Remove containers & networks"
	@echo "make rebuild      - Rebuild and restart all services"

# Build images
build:
	@echo "Building Docker images..."
	docker-compose build

# Start services
up:
	@echo "Starting services..."
	docker-compose up -d
	@echo "Services started! Check logs with: make logs-follow"

# Stop services
down:
	@echo "Stopping services..."
	docker-compose down

# Restart services
restart: down up
	@echo "Services restarted!"

# View logs
logs:
	docker-compose logs app

logs-follow:
	docker-compose logs -f app

# Shell access
shell-app:
	docker-compose exec app bash

# Show status
ps:
	docker-compose ps

# Health check
health:
	@echo "Checking app health..."
	@curl -s http://localhost:8888/health | jq . || echo "App is not responding"

# Clean up everything
clean:
	@echo "Removing containers and networks..."
	docker-compose down
	@echo "Cleanup completed!"

# Rebuild and restart
rebuild: build restart
	@echo "Rebuild and restart completed!"

# View app logs with tail
tail-app:
	docker-compose logs -f --tail=50 app

# Save logs to file
save-logs:
	@echo "Saving logs to logs.txt..."
	docker-compose logs > logs_$(shell date +%Y%m%d_%H%M%S).txt
	@echo "Logs saved!"
