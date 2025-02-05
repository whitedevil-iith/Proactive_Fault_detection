import os
import random
import subprocess
import threading
import time
import numpy as np
import signal
import sys

stop_event = threading.Event()  # Global event to signal all threads to stop

# Global list to track PIDs of stress processes
stress_pids = []
lock = threading.Lock()  # For thread-safe access to the stress_pids list
packetLoss_Containers = None

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
    global stress_pids
    if typeOfStress == 0:
        print(f"No stress applied to container {container_id}.")
        time.sleep(d)
        return

    try:
        if stop_event.is_set():
            print(f"Stop signal received, aborting stress on container {container_id}.")
            return

        if typeOfStress == 1:  # CPU stress
            cpu_cores = 2
            remaining_time = d
            current_stress = percentageOfStress

            while remaining_time > 0:
                if stop_event.is_set():
                    print(f"Stop signal received, aborting CPU stress on container {container_id}.")
                    return
                step_duration = random.randint(0, remaining_time)
                remaining_time -= step_duration
                step_stress = random.randint(current_stress, percentageOfStressEnd)

                stress_cmd = f"docker exec -it {container_id} bash -c 'stress-ng --cpu {cpu_cores} --cpu-load {step_stress} --timeout {step_duration}s' "
                print(f"Applying CPU stress on container {container_id}: {stress_cmd}")
                proc = subprocess.Popen(stress_cmd, shell=True)
                with lock:
                    stress_pids.append(proc.pid)
                proc.wait()  # Wait for this step to complete
                current_stress = step_stress

        elif typeOfStress == 2:  # Memory stress
            remaining_time = d
            current_stress = percentageOfStress

            while remaining_time > 0:
                if stop_event.is_set():
                    print(f"Stop signal received, aborting Memory stress on container {container_id}.")
                    return
                step_duration = random.randint(0, remaining_time)
                remaining_time -= step_duration
                step_stress = random.randint(current_stress, percentageOfStressEnd)
                stress_cmd = f"docker exec -it {container_id} bash -c 'stress-ng --vm 1 --vm-bytes {step_stress}% --timeout {step_duration}s' "
                print(f"Applying Memory stress on container {container_id}: {stress_cmd}")
                proc = subprocess.Popen(stress_cmd, shell=True)
                with lock:
                    stress_pids.append(proc.pid)
                proc.wait()
                current_stress = step_stress

        elif typeOfStress == 3:  # Packet loss
            remaining_time = d
            current_stress = percentageOfStress

            cleanup_cmd = f"docker exec -it {container_id} bash -c 'tc qdisc del dev eth0 root netem' "
            os.system(cleanup_cmd)

            while remaining_time > 0:
                if stop_event.is_set():
                    print(f"Stop signal received, aborting Packet Loss stress on container {container_id}.")
                    return
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
                    stress_pids.append(proc.pid)
                time.sleep(step_duration)
                os.system(cleanup_cmd)  # Cleanup after each step
                current_stress = step_stress

            os.system("python3 pl_deleter.py")
            os.system(cleanup_cmd)  # Cleanup after each step


    except subprocess.CalledProcessError as e:
        print(f"Subprocess error applying stress to container {container_id}: {e}")
    except Exception as e:
        print(f"Error applying stress to container {container_id}: {e}")


def cleanup_stress():
    """
    Stop all stress processes and cleanup.
    """
    global stress_pids, stop_event
    print("\nCleaning up stress processes...")

    # Set the stop event to signal all threads to stop
    stop_event.set()

    with lock:
        for pid in stress_pids:
            try:
                os.kill(pid, signal.SIGTERM)
                print(f"Terminated process with PID {pid}")
            except OSError as e:
                print(f"Error terminating process with PID {pid}: {e}")
        stress_pids.clear()

    # Perform packet loss cleanup
    for PL_id in packetLoss_Containers:
        cmd = f"docker exec -it {PL_id} bash -c 'tc qdisc del dev eth0 root netem' "
        os.system(cmd)

    sys.exit(0)  # Exit after cleanup


def signal_handler(sig, frame):
    """
    Handle interrupt signal to perform cleanup.
    """
    cleanup_stress()

def main():
    global stress_pids, stop_event
    signal.signal(signal.SIGINT, signal_handler)  # Register the signal handler

    max_duration = 24 * 60 * 60  # 24 hours in seconds
    sum_duration = 0

    cmd = "docker ps --filter 'name=^cu' --filter 'name=^du' --format '{{.ID}}'"
    container_ids = subprocess.check_output(cmd, shell=True).decode().splitlines()
    print(f"Fetched container IDs: {container_ids}")
    packetLoss_Containers = container_ids

    while sum_duration <= max_duration:
        duration = int(np.random.exponential(scale=15) + 1)
        duration = min(max(duration, 300), 2700)
        sum_duration += duration

        threads = []
        for container_id in container_ids:
            type_probs = [1/2, 1/6, 1/6, 1/6]
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
            t.join()  # Wait for all threads to finish before starting new ones


if __name__ == "__main__":
    main()
