VENV = venv
PYTHON = $(VENV)/bin/python
SHELL := /bin/bash

install:
	@echo "Installing Python dependencies..."
	@$(VENV)/bin/pip install -r requirements.txt
	@echo "Installing supervisord..."
	@$(VENV)/bin/pip install supervisor

dev:
	@echo "[TODO] Starting development environment..."

build:
	@echo "Building Docker image..."
	@docker build -t wizenedchimp/therazzler:latest -f Razzler_Dockerfile .

run:
	@echo "Running Docker container..."
	@docker run --env-file .env -v $$(pwd)/data:/data -e DATA_DIR=/data -p 8573:8573 wizenedchimp/therazzler:latest

brun:
	@echo "Building Docker image..."
	@docker build -t wizenedchimp/therazzler:latest -f Razzler_Dockerfile .
	@echo
	@echo
	@echo "Running Docker container..."
	@echo
	@echo
	@docker run --env-file .env -v $$(pwd)/data:/data -e DATA_DIR=/data -p 8573:8573 wizenedchimp/therazzler:latest

publish:
	@echo "Building Docker image..."
	@docker build -t wizenedchimp/therazzler:latest -f Razzler_Dockerfile .
	@echo "Publishing Docker image to Docker Hub..."
	@docker push wizenedchimp/therazzler:latest
