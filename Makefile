.DEFAULT_GOAL:=help

.PHONY: docker-db-run
docker-db-run: ## Run docker container with database
	docker run -d --name constraints-db \
		-p 15433:5432 \
		-e POSTGRES_USER=docker \
		-e POSTGRES_PASSWORD=docker \
		-e POSTGRES_DB=docker \
		postgres:9.6.2

.PHONY: help
help: ## Show this help
	@echo "Makefile for LemonPI Constraints package\n"
	@fgrep -h "##" $(MAKEFILE_LIST) | \
	fgrep -v fgrep | sed -e 's/## */##/' | column -t -s##

.PHONY: setup
setup: ##Create Python virtualenv to run application in
setup: venv

.PHONY: test
test: ## Run all unit tests
test: venv
	@. venv/bin/activate; \
	py.test -s ./tests

venv: requirements.txt test-requirements.txt
	virtualenv $@; \
	. ./$@/bin/activate; \
	pip install -r requirements.txt; \
	pip install -r test-requirements.txt
	@touch venv
