PYTHON ?= python

.PHONY: up down logs test lint auth worker scheduler api

up:
	docker compose up -d

down:
	docker compose down

logs:
	docker compose logs -f

test:
	$(PYTHON) -m pytest

lint:
	ruff check .
	mypy app

auth:
	$(PYTHON) scripts/auth_playwright.py

worker:
	$(PYTHON) -m app.workers.worker

scheduler:
	$(PYTHON) -m app.services.rss

api:
	uvicorn app.main:app --reload --host 0.0.0.0 --port 8080
