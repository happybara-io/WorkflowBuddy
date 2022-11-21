.PHONY: format test

prep: format test

format:
	poetry run black .

ngrok:
	ngrok http 4747

run-dev:
	./run-dev.sh

test:
	poetry run python -m pytest -sv tests/

cov:
	poetry run python -m pytest --cov=. -sv tests/

type-check:
	poetry run python -m mypy buddy/ # app.py

generate-requirements:
	poetry export -o requirements.txt --without-hashes

up:
	docker compose up

up-build:
	docker compose up --build

setup-precommit-hooks:
	poetry run pre-commit install
