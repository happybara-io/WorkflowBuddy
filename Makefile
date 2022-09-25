.PHONY: fmt

fmt:
	poetry run black .

ngrok:
	ngrok http 3000

serve:
	./run.sh