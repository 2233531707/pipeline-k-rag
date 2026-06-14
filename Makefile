
.PHONY: up up-lite down logs lint format seed reset sync-test-up sync-test-rebuild sync-test-status sync-test-stop

PYTEST_ARGS ?=
SYNC_TEST_COMPOSE = docker compose --env-file .env -p yuxi-sync-isolated -f docker-compose.yml -f .docker-compose.sync-test.yml

up:
	@if [ ! -f .env ]; then \
		echo "Error: .env file not found. Please create it from .env.template"; \
		exit 1; \
	fi
	bash scripts/check_data_volumes.sh
	docker compose up -d

down:
	docker compose down

reset:
	@if [ ! -f .env ]; then \
		echo "Error: .env file not found. Please create it from .env.template"; \
		exit 1; \
	fi
	docker compose down
	rm -rf docker/volumes
	docker compose up -d
	@echo "Waiting for api to be ready..."
	@until docker compose exec -T api true >/dev/null 2>&1; do sleep 2; done
	$(MAKE) seed

up-lite:
	@if [ ! -f .env ]; then \
		echo "Error: .env file not found. Please create it from .env.template"; \
		exit 1; \
	fi
	bash scripts/check_data_volumes.sh
	LITE_MODE=true VITE_USE_RUNS_API=false docker compose up -d postgres redis minio api web

logs:
	@docker logs --tail=50 api-dev
	@echo "\n\nBranch: $$(git branch --show-current)"
	@echo "Commit ID: $$(git rev-parse HEAD)"
	@echo "System: $$(uname -a)"

sync-test-up:
	@test -f .env || (echo "Error: .env file not found in the isolated worktree" && exit 1)
	$(SYNC_TEST_COMPOSE) up -d --no-build

sync-test-rebuild:
	@test -f .env || (echo "Error: .env file not found in the isolated worktree" && exit 1)
	@test -f web/dist/index.html || (echo "Error: run the frontend build before rebuilding the isolated Web image" && exit 1)
	$(SYNC_TEST_COMPOSE) up -d --build

sync-test-status:
	$(SYNC_TEST_COMPOSE) ps -a

sync-test-stop:
	$(SYNC_TEST_COMPOSE) stop

seed:
	docker compose exec api uv run python scripts/seed_initial_users.py

######################
# LINTING AND FORMATTING
######################

format:
	cd backend && uv run ruff format package
	cd backend && uv run ruff check package --fix
	cd backend && uv run ruff check --select I package --fix
	cd web && pnpm run format
	cd web && pnpm run lint
