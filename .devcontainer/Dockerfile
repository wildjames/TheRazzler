# Use the official Python 3.11 image from the Docker Hub
FROM mcr.microsoft.com/vscode/devcontainers/python:3.11

# Install system dependencies and development tools
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libc-dev \
    curl \
    git \
    ssh \
    vim \
    build-essential \
    zsh \
    direnv \
    supervisor && \
    rm -rf /var/lib/apt/lists/*

# Set up ZSH as root
RUN mkdir -p /home/vscode/.antigen
RUN curl -L git.io/antigen > /home/vscode/.antigen/antigen.zsh
COPY .dockershell.sh /home/vscode/.zshrc
RUN chown -R vscode:vscode /home/vscode/.antigen /home/vscode/.zshrc

# Switch to the vscode
USER vscode

# Set the working directory in the container
WORKDIR /setup

# Get set up with the shell
RUN /bin/zsh /home/vscode/.zshrc

# Install Python dependencies
COPY requirements.txt /setup/requirements.txt
RUN pip install --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt \
    && pip install gunicorn

# Set up Supervisord configuration
COPY supervisord.conf /etc/supervisor/conf.d/supervisord.conf

# Expose the port Flask is accessible on
EXPOSE 8573

# Enable direnv
RUN echo 'eval "$(direnv hook bash)"' >> ~/.bashrc

# Set working directory
WORKDIR /app

