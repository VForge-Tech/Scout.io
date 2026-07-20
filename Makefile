.PHONY: setup dev test migrate test-backend test-frontend lint format docker-up docker-down

setup:
	@echo "=== Setting up Backend Virtual Environment ==="
	python -m venv backend/.venv
	-backend/.venv/Scripts/python -m pip install --upgrade pip
	-backend/.venv/bin/python -m pip install --upgrade pip
	backend/.venv/Scripts/pip install -r backend/requirements.txt || backend/.venv/bin/pip install -r backend/requirements.txt
	@echo "=== Setting up Frontend dependencies ==="
	cd frontend && (npm.cmd install --legacy-peer-deps || npm install --legacy-peer-deps)

dev:
	@echo "=== Starting Dev Environment via Docker Compose ==="
	docker compose up --build

test: test-backend test-frontend

test-backend:
	@echo "=== Running Backend Unit Tests ==="
	backend/.venv/Scripts/pytest backend/tests || backend/.venv/bin/pytest backend/tests

test-frontend:
	@echo "=== Running Frontend Unit Tests ==="
	cd frontend && (npm.cmd test || npm test)

migrate:
	@echo "=== Running Alembic Database Migrations ==="
	cd backend && (.venv/Scripts/alembic upgrade head || .venv/bin/alembic upgrade head || alembic upgrade head)

lint:
	@echo "=== Linting Backend (ruff) ==="
	backend/.venv/Scripts/ruff check backend || backend/.venv/bin/ruff check backend || ruff check backend
	@echo "=== Linting Frontend (eslint) ==="
	cd frontend && (npm.cmd run lint || npm run lint)

format:
	@echo "=== Formatting Backend (ruff format) ==="
	backend/.venv/Scripts/ruff format backend || backend/.venv/bin/ruff format backend || ruff format backend
	@echo "=== Formatting Frontend (prettier) ==="
	cd frontend && (npm.cmd run format || npm run format)

docker-up:
	docker compose up -d

docker-down:
	docker compose down
