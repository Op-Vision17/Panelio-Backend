.PHONY: install dev migrate makemigrations shell

# Install project dependencies
install:
	poetry install

# Run the development server
dev:
	poetry run uvicorn app.main:app --reload

fmt:
	poetry run isort .
	poetry run black .

# Apply database migrations
migrate:
	poetry run alembic upgrade head

# Create a new database migration
# Usage: make makemigrations m="Migration message"
makemigrations:
	poetry run alembic revision --autogenerate -m "$(m)"

# Open poetry shell
shell:
	poetry shell
