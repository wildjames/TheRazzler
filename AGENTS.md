# Project Overview

This repository contains the code for **The Razzler**, a multi-process application that integrates the Signal messaging service with OpenAI models. It listens for Signal messages, stores them in Redis/MongoDB, processes them via a collection of command handlers ("the brain"), then replies or reacts using Signal. A small Flask API is provided to allow users to update their preferences.

The project is structured into several components which communicate through RabbitMQ queues:

* **signal_interface/** – Interface to the Signal API. Contains data models and the consumer/producer classes that handle inbound/outbound Signal messages.
* **razzler_brain/** – Implements the message processing logic. The main class `RazzlerBrain` consumes messages from RabbitMQ and dispatches to command handlers located in `razzler_brain/commands/`.
* **ai_interface/** – Wrapper around the OpenAI SDK, used by the brain commands for chat, vision and image generation functionality.
* **user_prefs_api/** – Flask application exposing endpoints to manage user preferences stored in MongoDB. It also issues and verifies OTP codes.
* **utils/** – Shared helpers for configuration loading, Redis/MongoDB connections, phonebook management and local file storage.
* **main.py** – Entry point when running in Docker or locally. Loads `config.yaml` from the `data` directory and spawns producer/consumer/brain processes.

Other notable files:

* `AAA_example_config.yaml` – Example configuration file showing all available options.
* `dev_runner.py` – Watches the source tree and restarts the application when files change (used with `supervisord_dev.conf`).
* `Razzler_Dockerfile` and `.devcontainer/` – Docker setup for production and development environments.
* `supervisord.conf` and `supervisord_dev.conf` – Process manager configuration used in Docker/dev.

# Directory Guide

```
├── ai_interface/        # GPTInterface and OpenAI dataclasses
├── razzler_brain/       # RazzlerBrain core and command handlers
│   └── commands/        # Individual commands (reply, react, create_image, ...)
├── signal_interface/    # Signal API consumer/producer and message models
├── user_prefs_api/      # Flask API for user preferences and OTP login
├── utils/               # Configuration helpers, storage, Redis/Mongo utilities
├── main.py              # Launches producers, consumers and brains
└── AAA_example_config.yaml  # Sample configuration
```

# Running Locally

1. Ensure `OPENAI_API_KEY` and `DATA_DIR` are exported. `DATA_DIR` should contain `config.yaml` similar to `AAA_example_config.yaml`.
2. Install dependencies using the `Makefile`:
   ```sh
   make install
   ```
3. Start the development stack with hot reloading:
   ```sh
   make dev
   ```
   This runs `supervisord_dev.conf` which launches both the Flask API and the Razzler processes.

# Testing

No automated test suite is included. When adding tests in the future, store them under a `tests/` directory and document how to run them here.

