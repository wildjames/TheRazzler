#!/bin/bash

# Check if an argument is provided
if [ "$#" -ne 1 ]; then
    echo "Usage: ./trust_number_command.sh <number>"
    exit 1
fi

# Get the number from the command-line argument
number=$1

# Send the cURL request
curl -X PUT -H "Content-Type: application/json" "http://192.168.0.111:8231/v1/identities/+447808723931/trust/${number}" -d '{"trust_all_known_keys": true}'
