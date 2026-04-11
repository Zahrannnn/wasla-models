.PHONY: help build up down restart logs ps health clean test

help: ## Show this help message
	@echo "Wasla AI Agent - Docker Commands"
	@echo ""
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-15s\033[0m %s\n", $$1, $$2}'

build: ## Build the Docker images
	docker-compose build

up: ## Start all services
	docker-compose up -d

down: ## Stop all services
	docker-compose down

restart: ## Restart all services
	docker-compose restart

logs: ## View logs
	docker-compose logs -f

ps: ## Show running containers
	docker-compose ps

health: ## Check health status
	curl -s http://localhost:8000/health | python -m json.tool

test: ## Run quick API test
	curl -X POST http://localhost:8000/api/chat/test-company \
		-H "Content-Type: application/json" \
		-d '{"prompt": "Hello!", "conversation_history": []}'

clean: ## Stop and remove containers, volumes, and images
	docker-compose down -v --rmi all

rebuild: down build up ## Rebuild and restart

shell: ## Access application shell
	docker-compose exec wasla-ai-agent bash
