#!/bin/bash

# Get a list of container IDs whose names contain "cu", "du", "ue", or "open5gs"
container_ids=$(docker ps -aq --filter "name=cu" --filter "name=du" --filter "name=ue" --filter "name=open5gs")

if [ -z "$container_ids" ]; then
    echo "No containers found with names containing 'cu', 'du', 'ue', or 'open5gs'."
else
    echo "The following containers will be removed:"
    docker ps -a --filter "name=cu" --filter "name=du" --filter "name=ue" --filter "name=open5gs" --format "table {{.ID}}\t{{.Names}}"

    # Force remove the containers
    docker rm -f $container_ids
    echo "Removed containers."
fi
