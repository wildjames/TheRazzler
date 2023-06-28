#!/bin/bash

# Check if an argument is provided
if [ "$#" -ne 1 ]; then
    echo "Usage: ./send_request.sh <number>"
    exit 1
fi

# Get the number from the command-line argument
number=$1

# Send the cURL request
curl -X PUT -H "Content-Type: application/json" "http://127.0.0.1:8080/v1/identities/+447743992060/trust/${number}" -d '{"trust_all_known_keys": true}'
