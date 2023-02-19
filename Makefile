.PHONY: format test

prep: format test

format:
	poetry run black buddy/ tests/ app.py

ngrok:
	ngrok http 4747

run-dev:
	poetry run ./run-dev.sh

test:
	poetry run python -m pytest -sv tests/

cov:
	poetry run python -m pytest --cov-report html --cov-report term --cov=. -sv tests/
	# wslview for linux on windows - on Mac you can use 'open', on linux 'xdg-open'
	wslview htmlcov/index.html || true

typecheck:
	poetry run python -m mypy --no-warn-unused-ignores buddy/ # app.py

generate-requirements:
	poetry export -o requirements.txt --without-hashes

up:
	docker compose up

up-build:
	docker compose up --build

setup-precommit-hooks:
	poetry run pre-commit install
