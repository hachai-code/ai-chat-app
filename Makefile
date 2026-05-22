.PHONY: install dev test lint

install:
	uv sync
	cd frontend && npm install

# Run backend + frontend dev servers together; Ctrl-C kills both.
dev:
	@trap 'kill 0' EXIT; \
	uv run uvicorn backend.main:app --reload --port 8000 & \
	(cd frontend && npm run dev) & \
	wait

test:
	uv run pytest backend/test_main.py -v

lint:
	uv run ruff check backend/
	cd frontend && npm run lint
