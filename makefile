# Makefile

run:
	uvicorn main:app --reload

build:
	docker build -t pennywise .

serve:
	docker run -p 8000:8000 pennywise
