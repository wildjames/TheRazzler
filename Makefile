VENV = venv
PYTHON = $(VENV)/bin/python

install:
	@echo "Installing Python dependencies..."
	@$(VENV)/bin/pip install -r requirements.txt
	@echo "Installing supervisord..."
	@$(VENV)/bin/pip install supervisor

dev:
	@echo "[TODO] Starting development environment..."

prod:
	@echo "Starting production environment..."
	@$(VENV)/bin/supervisord -c supervisord.conf

publish:
	@echo "Building Docker image..."
	@docker build -t wizenedchimp/therazzler:latest -f Razzler_Dockerfile .
	@echo "Publishing Docker image to Docker Hub..."
	@docker push wizenedchimp/therazzler:latest
