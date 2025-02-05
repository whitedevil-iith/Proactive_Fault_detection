import os
import random
import subprocess
import threading
import time
import numpy as np
import signal
import sys
import csv

# Global list to track PIDs of stress processes
stress_pids = []
lock = threading.Lock()  # For thread-safe access to the stress_pids list
packetLoss_Containers = None
file = {}
save_thread = None

# Run the Docker command to get the container IDs
command = "docker ps -a --filter 'name=cu' --filter 'name=du' -q"
container_ids = subprocess.check_output(command, shell=True).decode().strip().split('\n')

# Initialize the file dictionary
for cid in container_ids:
    file[cid] = [0, 0]


import csv
import threading
import time

# Assuming 'file' is your global dictionary containing the stress type for each container
# Example:
# file = {'container1': (1, 70), 'container2': (2, 80)}


import csv
import time

# Assuming 'file' is your global dictionary containing the stress type and step stress for each container
# Example:
# file = {'container1': (1, 70), 'container2': (2, 80)}

# Function to save the 'file' dictionary to a CSV file every 1 second
def save_to_file():
    """Function to save the 'file' dictionary to 'file_data.csv' and append to 'test.csv' every 1 second."""
    while True:
        with lock:
            # Prepare the row with the current data
            row = {}
            for cid, (stress_type, step_stress) in file.items():
                row[f"{cid}_stressType"] = stress_type
                row[f"{cid}_stepStress"] = step_stress

            # Save to 'file_data.csv' (overwrite each time)
            with open('file_data.csv', 'w', newline='') as csvfile:
                # Define the fieldnames (dynamic columns based on container IDs)
                fieldnames = ['Timestamp']  # Optional, if you want a timestamp

                # Dynamically create fieldnames for each container
                for cid in file.keys():
                    fieldnames.append(f"{cid}_stressType")
                    fieldnames.append(f"{cid}_stepStress")

                # Create the CSV writer
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)

                # Write the header once
                writer.writeheader()

                # Write the row into the CSV file
                writer.writerow(row)
            
            print("Data saved to 'file_data.csv'.")

            # Append to 'test.csv' (append mode)
            with open('test.csv', 'a', newline='') as test_csvfile:
                # If the file is empty, write the header first
                if test_csvfile.tell() == 0:
                    fieldnames = ['Timestamp']
                    for cid in file.keys():
                        fieldnames.append(f"{cid}_stressType")
                        fieldnames.append(f"{cid}_stepStress")

                    writer = csv.DictWriter(test_csvfile, fieldnames=fieldnames)
                    writer.writeheader()

                # Write the row into 'test.csv'
                writer = csv.DictWriter(test_csvfile, fieldnames=fieldnames)
                writer.writerow(row)
            
            print("Data appended to 'test.csv'.")

        # Save every 1 second
        time.sleep(1)





def ensure_stress_ng_installed(container_id):
    """Ensure that stress-ng is installed in the container."""
    try:
        install_cmd = f"docker exec -it {container_id} bash -c 'apt update && apt install -y stress-ng'"
        print(f"Installing stress-ng on container {container_id}: {install_cmd}")
        os.system(install_cmd)
    except Exception as e:
        print(f"Error installing stress-ng on container {container_id}: {e}")


def injectStress(container_id, typeOfStress, d, percentageOfStress, percentageOfStressEnd):
    """Inject stress into a Docker container based on the specified type."""
    global stress_pids
    # with lock:
        # file[container_id] = typeOfStress

    if typeOfStress == 0:
        print(f"No stress applied to container {container_id}.")
        time.sleep(d)
        with lock:
            file[container] = [0,0]
        return

    try:
        if typeOfStress == 1:  # CPU stress
            cpu_cores = 2
            remaining_time = d
            current_stress = percentageOfStress

            while remaining_time > 0:
                step_duration = random.randint(60, remaining_time)
                remaining_time -= step_duration
                step_stress = random.randint(current_stress, percentageOfStressEnd)

                with lock:
                    file[container_id] = [typeOfStress, step_stress]
                stress_cmd = f"docker exec -it {container_id} bash -c 'stress-ng --cpu {cpu_cores} --cpu-load {step_stress} --timeout {step_duration}s'"
                print(f"Applying CPU stress on container {container_id}: {stress_cmd}")
                proc = subprocess.Popen(stress_cmd, shell=True)
                with lock:
                    stress_pids.append(proc.pid)
                proc.wait()
                current_stress = step_stress

        elif typeOfStress == 2:  # Memory stress
            remaining_time = d
            current_stress = percentageOfStress

            while remaining_time > 0:
                step_duration = random.randint(60, remaining_time)
                remaining_time -= step_duration
                step_stress = random.randint(current_stress, percentageOfStressEnd)

                with lock:
                    file[container_id] = [typeOfStress, step_stress]
                stress_cmd = f"docker exec -it {container_id} bash -c 'stress-ng --vm 1 --vm-bytes {step_stress}% --timeout {step_duration}s'"
                print(f"Applying Memory stress on container {container_id}: {stress_cmd}")
                proc = subprocess.Popen(stress_cmd, shell=True)
                with lock:
                    stress_pids.append(proc.pid)
                proc.wait()
                current_stress = step_stress

        elif typeOfStress == 3:  # Packet loss
            remaining_time = d
            current_stress = percentageOfStress

            cleanup_cmd = f"docker exec -it {container_id} bash -c 'tc qdisc del dev eth0 root netem'"
            os.system(cleanup_cmd)

            while remaining_time > 0:
                step_duration = random.randint(60, remaining_time)
                remaining_time -= step_duration
                step_stress = random.randint(current_stress, percentageOfStressEnd)

                try:
                    tc_cmd = f"docker exec -it {container_id} bash -c 'tc qdisc add dev eth0 root netem loss {step_stress}%'"
                    print(f"Applying Packet Loss on container {container_id}: {tc_cmd}")
                    proc = subprocess.Popen(tc_cmd, shell=True)
                except Exception as e:
                    print(e)
                    os.system(cleanup_cmd)
                    proc = subprocess.Popen(tc_cmd, shell=True)

                with lock:
                    file[container_id] = [typeOfStress, step_stress]

                with lock:
                    stress_pids.append(proc.pid)
                time.sleep(step_duration)
                os.system(cleanup_cmd)  # Cleanup after each step
                current_stress = step_stress
            os.system("python3 pl_deleter.py")

    except subprocess.CalledProcessError as e:
        print(f"Subprocess error applying stress to container {container_id}: {e}")
    except Exception as e:
        print(f"Error applying stress to container {container_id}: {e}")


def cleanup_stress():
    """Stop all stress processes and cleanup."""
    global stress_pids
    print("\nCleaning up stress processes...")
    with lock:
        for pid in stress_pids:
            try:
                os.kill(pid, signal.SIGTERM)
                print(f"Terminated process with PID {pid}")
            except OSError as e:
                print(f"Error terminating process with PID {pid}: {e}")
        stress_pids.clear()
    sys.exit(0)


def signal_handler(sig, frame):
    """Handle interrupt signal to perform cleanup."""
    cleanup_stress()


def main():
    global stress_pids
    signal.signal(signal.SIGINT, signal_handler)  # Register the signal handler

    max_duration = 24 * 60 * 60  # 24 hours in seconds
    sum_duration = 0

    max_duration = 10*60

    cmd = "docker ps --filter 'name=^cu' --filter 'name=^du' --format '{{.ID}}'"
    container_ids = subprocess.check_output(cmd, shell=True).decode().splitlines()
    print(f"Fetched container IDs: {container_ids}")
    packetLoss_Containers = container_ids

    # Start the background thread to save the 'file' dictionary every 500ms
    global save_thread
    save_thread = threading.Thread(target=save_to_file)
    save_thread.daemon = True  # This makes sure the thread will exit when the main program exits
    save_thread.start()

    while sum_duration <= max_duration:
        duration = int(np.random.exponential(scale=15) + 1)
        duration = min(max(duration, 60), 300)
        sum_duration += duration

        threads = []
        for container_id in container_ids:
            type_probs = [1 / 2, 1 / 6, 1 / 6, 1 / 6]
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
