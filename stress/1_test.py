import os
import random
import subprocess
import threading
import time
import numpy as np
import signal
import sys

# Global dictionary to track PIDs of stress processes by container ID
stress_pids_dict = {}
lock = threading.Lock()  # For thread-safe access to the stress_pids_dict

def ensure_stress_ng_installed(container_id):
    """
    Ensure that stress-ng is installed in the container.
    """
    try:
        install_cmd = f"docker exec -it {container_id} bash -c 'apt update && apt install -y stress-ng' "
        print(f"Installing stress-ng on container {container_id}: {install_cmd}")
        os.system(install_cmd)
    except Exception as e:
        print(f"Error installing stress-ng on container {container_id}: {e}")

def injectStress(container_id, typeOfStress, d, percentageOfStress, percentageOfStressEnd):
    """
    Inject stress into a Docker container based on the specified type.
    """
    global stress_pids_dict
    if typeOfStress == 0:
        print(f"No stress applied to container {container_id}.")
        time.sleep(d)
        return

    try:
        if typeOfStress == 1:  # CPU stress
            cpu_cores = 2  # Assuming 2 CPU cores for stress-ng
            remaining_time = d
            current_stress = percentageOfStress

            while remaining_time > 0:
                step_duration = random.randint(0, remaining_time)
                remaining_time -= step_duration
                step_stress = random.randint(current_stress, percentageOfStressEnd)

                stress_cmd = f"docker exec -it {container_id} bash -c 'stress-ng --cpu {cpu_cores} --cpu-load {step_stress} --timeout {step_duration}s' "
                print(f"Applying CPU stress on container {container_id}: {stress_cmd}")
                proc = subprocess.Popen(stress_cmd, shell=True)
                
                with lock:
                    if container_id not in stress_pids_dict:
                        stress_pids_dict[container_id] = []
                    stress_pids_dict[container_id].append(proc.pid)
                
                proc.wait()  # Wait for this step to complete
                current_stress = step_stress

        elif typeOfStress == 2:  # Memory stress
            remaining_time = d
            current_stress = percentageOfStress

            while remaining_time > 0:
                step_duration = random.randint(0, remaining_time)
                remaining_time -= step_duration
                step_stress = random.randint(current_stress, percentageOfStressEnd)
                stress_cmd = f"docker exec -it {container_id} bash -c 'stress-ng --vm 1 --vm-bytes {step_stress}% --timeout {step_duration}s' "
                print(f"Applying Memory stress on container {container_id}: {stress_cmd}")
                proc = subprocess.Popen(stress_cmd, shell=True)
                
                with lock:
                    if container_id not in stress_pids_dict:
                        stress_pids_dict[container_id] = []
                    stress_pids_dict[container_id].append(proc.pid)

                proc.wait()
                current_stress = step_stress

        elif typeOfStress == 3:  # Packet loss
            remaining_time = d
            current_stress = percentageOfStress

            cleanup_cmd = f"docker exec -it {container_id} bash -c 'tc qdisc del dev eth0 root netem' "
            os.system(cleanup_cmd)

            while remaining_time > 0:
                step_duration = random.randint(0, remaining_time)
                remaining_time -= step_duration
                step_stress = random.randint(current_stress, percentageOfStressEnd)
                try:
                    tc_cmd = f"docker exec -it {container_id} bash -c 'tc qdisc add dev eth0 root netem loss {step_stress}%' "
                    print(f"Applying Packet Loss on container {container_id}: {tc_cmd}")
                    proc = subprocess.Popen(tc_cmd, shell=True)
                except Exception as e:
                    print(e)
                    os.system(cleanup_cmd)
                    print(f"Applying Packet Loss on container {container_id}: {tc_cmd}")
                    proc = subprocess.Popen(tc_cmd, shell=True)

                with lock:
                    if container_id not in stress_pids_dict:
                        stress_pids_dict[container_id] = []
                    stress_pids_dict[container_id].append(proc.pid)

                time.sleep(step_duration)
                os.system(cleanup_cmd)  # Cleanup after each step
                current_stress = step_stress

    except subprocess.CalledProcessError as e:
        print(f"Subprocess error applying stress to container {container_id}: {e}")
    except Exception as e:
        print(f"Error applying stress to container {container_id}: {e}")


def cleanup_stress():
    """
    Stop all stress processes and cleanup.
    """
    global stress_pids_dict
    print("\nCleaning up stress processes...")
    
    with lock:
        for container_id, pids in stress_pids_dict.items():
            for pid in pids:
                try:
                    # Using `docker exec` to kill the process inside the container
                    kill_cmd = f"docker exec -it {container_id} bash -c 'kill {pid}'"
                    subprocess.run(kill_cmd, shell=True, check=True)
                    print(f"Terminated process with PID {pid} in container {container_id}")
                except subprocess.CalledProcessError as e:
                    print(f"Error terminating process with PID {pid} in container {container_id}: {e}")
                except Exception as e:
                    print(f"Unexpected error while terminating process {pid} in container {container_id}: {e}")
            # Clean up the PID list for the container
            stress_pids_dict[container_id] = []

    sys.exit(0)


def signal_handler(sig, frame):
    """
    Handle interrupt signal to perform cleanup.
    """
    cleanup_stress()

def main():
    global stress_pids_dict
    signal.signal(signal.SIGINT, signal_handler)  # Register the signal handler

    max_duration = 24 * 60 * 60  # 24 hours in seconds
    sum_duration = 0

    cmd = "docker ps --filter 'name=^cu' --filter 'name=^du' --format '{{.ID}}'"
    container_ids = subprocess.check_output(cmd, shell=True).decode().splitlines()
    print(f"Fetched container IDs: {container_ids}")

    while sum_duration <= max_duration:
        duration = int(np.random.exponential(scale=15) + 1)
        duration = min(max(duration, 300), 2700)
        sum_duration += duration

        threads = []
        for container_id in container_ids:
            
            type_probs = [0, 0, 0, 1]  # Adjust probabilities as needed
            type_of_stress = np.random.choice([0, 1, 2, 3], p=type_probs)

            if type_of_stress == 0:
                percentage_of_stress_start = 0
                percentage_of_stress_end = 0
            elif type_of_stress == 1 or type_of_stress == 2:
                percentage_of_stress_start = np.random.randint(60, 101)
                percentage_of_stress_end = np.random.randint(percentage_of_stress_start, 101)
            elif type_of_stress == 3:
                percentage_of_stress_start = np.random.randint(1, 11)
                percentage_of_stress_end = np.random.randint(percentage_of_stress_start, 11)

            t = threading.Thread(
                target=injectStress,
                args=(container_id, type_of_stress, duration, percentage_of_stress_start, percentage_of_stress_end)
            )
            threads.append(t)
            t.start()

        for t in threads:
            t.join()

if __name__ == "__main__":
    main()
