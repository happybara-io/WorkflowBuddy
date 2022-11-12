.PHONY: fmt test

prep: fmt test

format:
	poetry run black .

ngrok:
	ngrok http 4747

run-dev:
	./run-dev.sh

test:
	poetry run python -m pytest -sv tests/

generate-requirements:
	poetry export -o requirements.txt --without-hashes

up:
	docker compose up

up-build:
	docker compose up --build

