#!/bin/bash

# Add the secondary IP address
ip addr add 10.53.10.2/16 dev eth0

# Execute the provided command (CMD from the Dockerfile)
exec "$@"

