import subprocess
import random
import time
import signal
import sys

container_pids = {}

def generate_random_sizes(total_ping_size, num_sizes, min_size=1):
    sizes = []
    sum_sizes = 0

    for _ in range(num_sizes - 1):
        size = random.randint(min_size, total_ping_size - sum_sizes)
        sizes.append(size)
        sum_sizes += size

    last_size = total_ping_size - sum_sizes
    if last_size < min_size:
        last_size = min_size
    sizes.append(last_size)

    return sizes


def start_ping(container_id, size, target_ip):
    try:
        max_ping_size = 60000  # Maximum size per ping command
        pids = []

        # Calculate the number of chunks needed
        num_pings = (size // max_ping_size) + (1 if size % max_ping_size > 0 else 0)

        for _ in range(num_pings):
            chunk_size = min(size, max_ping_size)  # Determine the size for this chunk
            cmd = (
                f"docker exec {container_id} bash -c "
                f"'ping -i 0.1 -s {chunk_size} {target_ip} > /dev/null 2>&1 & echo $!'"
            )
            pid = subprocess.check_output(cmd, shell=True, text=True).strip()

            if not pid.isdigit():
                raise ValueError(f"Unexpected PID output: {pid}")

            pids.append(pid)
            size -= chunk_size  # Reduce the remaining size

        return pids

    except (subprocess.CalledProcessError, ValueError) as e:
        print(f"Error starting ping in container {container_id}: {e}")
        return []


def stop_ping(container_id, pids):
    try:
        if not pids:
            print(f"No pids to stop for container {container_id}")
            return
        
        # Loop through all pids and stop them
        for pid in pids:
            cmd = f"docker exec {container_id} bash -c \"kill -9 {pid}\""
            subprocess.run(cmd, shell=True, check=True)
        
        print(f"Successfully stopped all pings in container {container_id}")
    except subprocess.CalledProcessError:
        print(f"Error stopping pings in container {container_id}")


def get_ping_target_ip(container_id):
    try:
        cmd = (
            f"docker exec {container_id} bash -c 'ip a show tun_srsue | "
            f"grep \"inet \" | awk \"{{print \\$2}}\" | cut -d\"/\" -f1'"
        )
        result = subprocess.check_output(cmd, shell=True, text=True).strip()
        return result
    except subprocess.CalledProcessError as e:
        print(f"Error retrieving IP for container {container_id}: {e}")
        return None

def start_iperf_server(container_id):
    try:
        cmd = f"docker exec {container_id} bash -c 'iperf -s > /dev/null 2>&1 &'"
        subprocess.run(cmd, shell=True, check=True)
        print(f"Started iperf server in container {container_id}")
    except subprocess.CalledProcessError as e:
        print(f"Error starting iperf server in {container_id}: {e}")

def start_iperf_client(container_id, target_ip):
    try:
        cmd = f"docker exec {container_id} bash -c 'iperf -c {target_ip} -t 3600 > /dev/null 2>&1 &'"
        subprocess.run(cmd, shell=True, check=True)
        print(f"Started iperf client in container {container_id} targeting {target_ip}")
    except subprocess.CalledProcessError as e:
        print(f"Error starting iperf client in {container_id}: {e}")

def stop_all_processes(container_id):
    try:
        cmd = f"docker exec {container_id} bash -c 'killall -9 iperf ping'"
        subprocess.run(cmd, shell=True, check=True)
        print(f"Stopped all processes in container {container_id}")
    except subprocess.CalledProcessError as e:
        print(f"Error stopping processes in {container_id}: {e}")

def signal_handler(sig, frame):
    print("\nStopping all processes...")
    for container_id in container_pids:
        stop_all_processes(container_id)
    sys.exit(0)

# Function to get Docker IDs
def get_docker_ids():
    try:
        cmd = "docker ps --filter 'name=^/ue' --format '{{.ID}}'"
        result = subprocess.check_output(cmd, shell=True, text=True)
        return result.strip().split('\n') if result.strip() else []
    except subprocess.CalledProcessError:
        print("Error retrieving Docker container IDs")
        return []


def main():
    signal.signal(signal.SIGINT, signal_handler)

    distribution = [
        11.0, 8.1, 5.6, 3.6, 2.7, 1.9, 3.0, 5.0, 7.1, 11.1, 11.2, 11.9,
        12.4, 12.3, 13.0, 13.1, 12.9, 12.7, 12.4, 12.2, 12.0, 13.0, 14.0, 15.0, 14.0
    ]

    distribution = [val / 16 for val in distribution]
    docker_ids = get_docker_ids()

    if not docker_ids:
        print("No Docker containers found.")
        return

    open5gs_container_id = subprocess.check_output("docker ps -q -f name=open5gs", shell=True, text=True).strip()
    if open5gs_container_id:
        start_iperf_server(open5gs_container_id)

    for container_id in docker_ids:
        target_ip = get_ping_target_ip(container_id)
        if target_ip:
            start_iperf_client(container_id, target_ip)

    for hour, current_distribution in enumerate(distribution, start=1):
        temp_size = current_distribution * 1_000_000_000
        total_ping_size = int(temp_size // 3600)
        sizes = generate_random_sizes(total_ping_size, len(docker_ids))

        for container_id, size in zip(docker_ids, sizes):
            target_ip = get_ping_target_ip(container_id)
            if target_ip:
                pids = start_ping(container_id, size, target_ip)
                container_pids[container_id] = pids

        time.sleep(1800)

    for container_id in docker_ids:
        stop_all_processes(container_id)
    if open5gs_container_id:
        stop_all_processes(open5gs_container_id)

if __name__ == "__main__":
    main()
