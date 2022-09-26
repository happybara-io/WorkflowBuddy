.PHONY: fmt

fmt:
	poetry run black .

ngrok:
	ngrok http 4747

serve:
	./run.sh

generate-requirements:
	poetry export -o requirements.txt

up:
	docker compose up

up-build:
	docker compose up --build

