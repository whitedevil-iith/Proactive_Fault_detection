#!/bin/bash

# Define the distribution as an array of floats (for example, for each hour)
distribution=(11.0 8.1 5.6 3.6 2.7 1.9 3.0 5.0 7.1 11.1 11.2 11.9 12.4 12.3 13.0 13.1 12.9 12.7 12.4 12.2 12.0 13.0 14.0 15.0 14.0)

# Get the number of hours (length of the distribution array)
no_of_hours=${#distribution[@]}

# Function to generate random sizes that total to the given `total_ping_size`
generate_random_sizes() {
  local total_ping_size=$1
  local num_sizes=$2
  local min_size=10000
  local max_size=60000

  local sum=0
  local sizes=()

  # Generate random sizes that sum to the total_ping_size
  for ((i=0; i<$num_sizes-1; i++)); do
    size=$((RANDOM % (max_size - min_size + 1) + min_size))
    sizes+=($size)
    sum=$((sum + size))
  done

  # Adjust the last size so that the total is equal to total_ping_size
  last_size=$((total_ping_size - sum))
  if ((last_size > max_size)); then
    last_size=$max_size
  elif ((last_size < min_size)); then
    last_size=$min_size
  fi
  sizes+=($last_size)

  echo "${sizes[@]}"
}

# Function to get the IP address of tun_srsue and decrement it by 1
get_ping_target_ip() {
  local container_id=$1

  echo "yashwnath"

  # Get the IP address of tun_srsue from the container
  ip_address=$(docker exec -it "$container_id" bash -c "ip a show tun_srsue | grep 'inet ' | awk '{print \$2}' | cut -d'/' -f1")

  # Decrement the last octet by 1
  IFS='.' read -r -a ip_parts <<< "$ip_address"
  last_octet=${ip_parts[3]}
  
  # Ensure the last octet is not 0
  if ((last_octet > 0)); then
    target_ip="${ip_parts[0]}.${ip_parts[1]}.${ip_parts[2]}.$((last_octet - 1))"
  else
    target_ip="${ip_parts[0]}.${ip_parts[1]}.${ip_parts[2]}.255"
  fi
  
  echo $target_ip
}

# Function to start ping in the container
start_ping() {
  local container_id=$1
  local size=$2
  local target_ip=$3

  echo "Starting ping in container $container_id with size $size and target IP $target_ip..."
  
  # Start ping command in background, capture its PID
  pid=$(docker exec -it "$container_id" bash -c "ping -i 0.1 -s $size $target_ip & echo \$!")

  # Return the PID of the ping process
  echo $pid
}

# Function to stop ping in the container
stop_ping() {
  local container_id=$1
  local pid=$2

  # Kill the ping process by PID
  echo "Killing ping process in container $container_id with PID $pid..."
  docker exec -it "$container_id" bash -c "kill -9 $pid"
  echo "Stopped ping in container $container_id."
}

# Iterate over each element of the distribution array, changing every hour
for ((hour=0; hour<$no_of_hours; hour++)); do
  # Get the current distribution value for the current hour
  current_distribution=${distribution[$hour]}
  
  # Calculate total_ping_size based on the current distribution (fixing the arithmetic)
  temp_size=$(echo "$current_distribution * 1000000000" | bc)
  total_ping_size=$(echo "$temp_size / 60 / 60" | bc)

  # Collect Docker IDs of running containers whose names start with 'ue'
  docker_ids=($(docker ps --filter "name=^/ue" --format "{{.ID}}"))

  # Output the distribution and total ping size for the current hour
  echo "Hour: $((hour + 1))"
  echo "Current Distribution: $current_distribution"
  echo "Total Ping Size: $total_ping_size bytes"

  # Randomize ping sizes for this hour, with total size summing to total_ping_size
  num_containers=${#docker_ids[@]}
  sizes=($(generate_random_sizes $total_ping_size $num_containers))

  # Declare an array to hold PIDs of ping processes for each container
  declare -A pids

  # Start the clock for this hour (loop until 1 hour is passed)
  start_time=$(date +%s)
  end_time=$((start_time + 3600)) # One hour later

  # Run ping in each container with randomized sizes in parallel
  while [[ $(date +%s) -lt $end_time ]]; do
    # Run ping for all containers in parallel
    for ((i=0; i<$num_containers; i++)); do
      container_id=${docker_ids[$i]}
      size=${sizes[$i]}
      
      # Get the target IP address (one less than the tun_srsue IP)
      target_ip=$(get_ping_target_ip "$container_id")
      
      # Start ping in the background and capture PID
      pids["$container_id"]=$(start_ping "$container_id" "$size" "$target_ip")
    done

    # Sleep for 10 seconds
    sleep 10

    # Now kill all the pings in parallel after 10 seconds
    for container_id in "${!pids[@]}"; do
      stop_ping "$container_id" "${pids[$container_id]}"
    done

    # Re-generate sizes for the next 10-second iteration
    sizes=($(generate_random_sizes $total_ping_size $num_containers))
  done

done

echo "Completed iterating through the distribution array."
