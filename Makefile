.DEFAULT_GOAL:=help

.PHONY: clean
clean: ## Remove all generated files
	@rm -rf doc/build
	@rm -rf venv

.PHONY: build-docs
build-docs: ## Build Sphinx documentation
build-docs: docs/build/index.html

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

.PHONY: report-lint
report-lint: ## Run PEP8 and PyLint linters
report-lint: report-pylint report-pep8

report-coverage: ## Compute code coverage
report-coverage: venv
	@echo "Computing code coverage of unit tests..."
	@. venv/bin/activate; \
	PYTHONPATH=. \
	coverage run --rcfile=./setup.cfg --source constraints/ -m py.test tests && \
	coverage report -m

.PHONY: report-pep8
report-pep8: ## Run PEP8
report-pep8: venv
	@echo "Checking for pep8 warnings..."
	@. venv/bin/activate; \
	PYTHONPATH=. \
	pep8 ${PKG_NAME} tests

.PHONY: report-pylint
report-pylint: ## Run PyLint
report-pylint: venv
	@echo "Checking for pylint warnings..."
	@. venv/bin/activate; \
	PYTHONPATH=. \
	pylint --rcfile setup.cfg --reports=n ${PKG_NAME} tests

.PHONY: setup
setup: ## Create Python virtualenv
setup: venv

.PHONY: test
test: ## Run all unit tests
test: venv
	@. venv/bin/activate; \
	py.test -s ./tests

.PHONY: run
run: ## Runs the web application
run: venv
	@. venv/bin/activate; \
	PYTHONPATH=. FLASK_APP=resources FLASK_DEBUG=1 \
	flask run

docs/build/index.html: venv docs/source/* constraints/*
	@. venv/bin/activate; \
	PYTHONPATH=. \
	sphinx-build -b html docs/source docs/build

venv: requirements.txt test-requirements.txt
	virtualenv $@; \
	. ./$@/bin/activate; \
	pip install -r requirements.txt; \
	pip install -r test-requirements.txt
	@touch venv



