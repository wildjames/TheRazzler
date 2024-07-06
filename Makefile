SHELL := /bin/bash

install:
	@echo "Setting up local development environment..."
	@python3 -m venv venv
	@source venv/bin/activate && pip install --upgrade pip && pip install -r requirements.txt
	@echo
	@echo
	@echo
	@echo "Local development environment setup complete. To activate the virtual environment, run:"
	@echo "source venv/bin/activate"

dev:
	@echo "Starting development environment..."
	@source .envrc && source venv/bin/activate && python3 dev_runner.py

build:
	@echo "Building Docker image..."
	@docker build -t wizenedchimp/therazzler:dev -f Razzler_Dockerfile .

run:
	@echo "Running Docker container..."
	@docker run --env-file .env -v $$(pwd)/data:/data -e DATA_DIR=/data -p 8573:8573 wizenedchimp/therazzler:dev

brun:
	@echo "Building Docker image..."
	@docker build -t wizenedchimp/therazzler:dev -f Razzler_Dockerfile .
	@echo
	@echo "Running Docker container..."
	@docker run --env-file .env -v $$(pwd)/data:/data -e DATA_DIR=/data -p 8573:8573 wizenedchimp/therazzler:dev

publish:
	@echo "Building Docker image..."
	@docker build -t wizenedchimp/therazzler:latest -f Razzler_Dockerfile .
	@echo "Publishing Docker image to Docker Hub..."
	@docker push wizenedchimp/therazzler:latest

clean:
	@echo "Cleaning up..."
	@rm -rf venv
	@echo "removing __pycache__ directories..."
	@find . -name "__pycache__" -type d -exec rm -rf {} +
	@echo "Cleanup complete."
