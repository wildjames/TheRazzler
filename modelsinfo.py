COSTS = {
    "gpt-3.5-turbo": {"prompt": 0.002, "completion": 0.002}, # Per 1k tokens
    "gpt-3.5-turbo-0301": {"prompt": 0.002, "completion": 0.002},
    "gpt-4-0314": {"prompt": 0.03, "completion": 0.06},
    "gpt-4": {"prompt": 0.03, "completion": 0.06},
    "text-embedding-ada-002": {"prompt": 0.0004, "completion": 0.0},
    "image": {"prompt": 0.02/1000, "completion": 0.02/1000}, # Per image
}
