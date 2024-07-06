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

# Create a devuser to run the application
RUN useradd -ms /bin/bash devuser

# Set up ZSH as root
RUN mkdir -p /home/devuser/.antigen
RUN curl -L git.io/antigen > /home/devuser/.antigen/antigen.zsh
COPY .dockershell.sh /home/devuser/.zshrc
RUN chown -R devuser:devuser /home/devuser/.antigen /home/devuser/.zshrc

# Switch to the devuser
USER devuser

# Set the working directory in the container
WORKDIR /setup

# Get set up with the shell
RUN /bin/zsh /home/devuser/.zshrc

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

