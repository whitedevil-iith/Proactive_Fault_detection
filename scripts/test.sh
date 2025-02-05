# Function to get the IP address of tun_srsue and decrement it by 1
get_ping_target_ip() {
  local container_id=$1
  echo "yashwanth"
  # Get the IP address of tun_srsue from the container
  ip_address=$(docker exec -it "$container_id" bash -c "ip a show tun_srsue | grep 'inet ' | awk '{print \$2}' | cut -d'/' -f1")
  echo "ip address is $ip_address"
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



      
# Get the target IP address (one less than the tun_srsue IP)

target_ip=$(get_ping_target_ip 28f7542bf621)


