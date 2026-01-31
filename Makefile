# Container Engine Configuration
export UID = $(shell id -u)
export GID = $(shell id -g)

PYTHON ?= uv run

ifneq ($(USE_PODMAN),)
	ENGINE := podman
	COMPOSE := podman-compose
	export PODMAN_USERNS = keep-id
else
	ENGINE := docker
	COMPOSE := docker compose
endif

# Command to prune only dangling images with our specific label
CLEAN_CMD := $(ENGINE) image prune -a -f --filter label=com.cyber.project="true"

.PHONY: install up update down logs build

init:
	@# Check for prerequisites
	@command -v git >/dev/null 2>&1 || { echo >&2 "Error: git is not installed."; exit 1; }
	@command -v $(ENGINE) >/dev/null 2>&1 || { echo >&2 "Error: $(ENGINE) is not installed."; exit 1; }

format:
	@$(PYTHON) ruff check . --fix
	@$(PYTHON) black .

lint:
	@$(PYTHON) ruff check .
	@$(PYTHON) black --check .
#	@$(PYTHON) mypy app

test:
	@$(PYTHON) pytest

up: init
	@echo "Starting Cyber using $(ENGINE)..."
	@$(COMPOSE) up -d

down: init
	@$(COMPOSE) down

logs: init
	@$(COMPOSE) logs -f

build: init
	@$(CLEAN_CMD)
	@$(COMPOSE) build

update: init
	@git pull origin master
	@$(COMPOSE) down
	@$(CLEAN_CMD)
	@$(COMPOSE) build --no-cache
