.PHONY: help up down logs be-install be-dev be-test be-lint fe-install fe-dev fe-test seed eval

help:
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN{FS=":.*?## "}{printf "  %-12s %s\n", $$1, $$2}'

up: ## Start the full stack with docker-compose
	docker compose up --build

down: ## Stop the stack
	docker compose down

logs: ## Tail all logs
	docker compose logs -f

be-install: ## Install backend deps
	cd backend && pip install -e ".[dev]"

be-dev: ## Run backend with reload
	cd backend && uvicorn app.main:app --reload

be-test: ## Run backend tests
	cd backend && pytest

be-lint: ## Lint + typecheck backend
	cd backend && ruff check . && mypy app

fe-install: ## Install frontend deps
	cd frontend && npm install

fe-dev: ## Run frontend dev server
	cd frontend && npm run dev

fe-test: ## Run frontend tests
	cd frontend && npm run test

seed: ## Load sample datasets + demo semantic layers (Phase 1)
	cd backend && insightiq seed

eval: ## Run the SQL-accuracy eval suite (Phase 5)
	cd backend && insightiq eval
