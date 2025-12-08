# Container Engine Configuration
export UID = $(shell id -u)
export GID = $(shell id -g)

ifneq ($(USE_PODMAN),)
	ENGINE := podman
	COMPOSE := podman-compose
else
	ENGINE := docker
	COMPOSE := docker compose
endif

.PHONY: install up update down logs

init:
	@# Check for prerequisites
	@command -v git >/dev/null 2>&1 || { echo >&2 "Error: git is not installed."; exit 1; }
	@command -v $(ENGINE) >/dev/null 2>&1 || { echo >&2 "Error: $(ENGINE) is not installed."; exit 1; }

up: init
	@echo "Starting Llama Coding using $(ENGINE)..."
	@$(COMPOSE) up -d --build
	@echo "Llama Coding is running at http://localhost:8000"

down:
	@$(COMPOSE) down

logs:
	@$(COMPOSE) logs -f

update:
	@git pull origin master
	@make down
	@make up
	@$(ENGINE) image prune -f