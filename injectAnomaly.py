import os
import random
import subprocess
import threading
import numpy as np

def injectStress(container_id, typeOfStress, d, percentageOfStress):
    """
    Inject stress into a Docker container based on the specified type.
    
    Parameters:
        container_id (str): The container ID.
        typeOfStress (int): Type of stress to apply (0: None, 1: CPU, 2: Memory, 3: Packet Loss).
        d (int): Duration of stress in seconds.
        percentageOfStress (int): Intensity of the stress as a percentage.
    """
    if typeOfStress == 0:
        print(f"No stress applied to container {container_id}.")
        return

    try:
        if typeOfStress == 1:  # CPU stress
            # Get the number of CPU cores used by the container
            cmd = f"docker exec -it {container_id} nproc"
            cpu_cores = int(subprocess.check_output(cmd, shell=True).decode().strip())

            # Apply CPU stress
            stress_cmd = f"docker exec -it {container_id} stress-ng --cpu {cpu_cores} --cpu-load {percentageOfStress} --timeout {d}s"
            print(f"Applying CPU stress on container {container_id}: {stress_cmd}")
            os.system(stress_cmd)

        elif typeOfStress == 2:  # Memory stress
            # Apply memory stress
            stress_cmd = f"docker exec -it {container_id} stress-ng --vm 1 --vm-bytes {percentageOfStress}% --timeout {d}s"
            print(f"Applying Memory stress on container {container_id}: {stress_cmd}")
            os.system(stress_cmd)

        elif typeOfStress == 3:  # Packet loss
            # Apply packet loss
            tc_cmd = f"docker exec -it {container_id} tc qdisc add dev eth0 root netem loss {percentageOfStress}%"
            print(f"Applying Packet Loss on container {container_id}: {tc_cmd}")
            os.system(tc_cmd)

            # Schedule removal of packet loss
            threading.Timer(d, lambda: os.system(f"docker exec -it {container_id} tc qdisc del dev eth0 root netem"))

    except Exception as e:
        print(f"Error applying stress to container {container_id}: {e}")


def main():
    max_duration = 24 * 60 * 60  # 24 hours in seconds
    sum_duration = 0
    
    while sum_duration <= max_duration:
        # Sample a duration from an exponential distribution (min 1 min, max 30 mins)
        duration = int(np.random.exponential(scale=15) + 1)  # Scale 15 for 30 mins max-like effect
        duration = min(max(duration, 60), 1800)  # Constrain between 1 min and 30 mins
        sum_duration += duration

        # Fetch container IDs with names starting with 'cu' or 'du'
        cmd = "docker ps --filter 'name=^cu' --filter 'name=^du' --format '{{.ID}}'"
        container_ids = subprocess.check_output(cmd, shell=True).decode().splitlines()

        print(f"Fetched container IDs: {container_ids}")

        threads = []

        for container_id in container_ids:
            # Sample a type of stress (0-3) using multinomial distribution
            type_probs = [0.25, 0.25, 0.25, 0.25]  # Equal probability for 0, 1, 2, 3
            type_of_stress = np.random.choice([0, 1, 2, 3], p=type_probs)

            # Determine percentage of stress based on type
            if type_of_stress == 0:
                percentage_of_stress = 0
            elif type_of_stress == 1 or type_of_stress == 2:
                percentage_of_stress = np.random.randint(60, 101)  # 60% to 100%
            elif type_of_stress == 3:
                percentage_of_stress = np.random.randint(1, 11)  # 1% to 10%

            # Create a thread for each stress application
            t = threading.Thread(
                target=injectStress,
                args=(container_id, type_of_stress, duration, percentage_of_stress)
            )
            threads.append(t)
            t.start()

        # Wait for all threads to complete
        for t in threads:
            t.join()

if __name__ == "__main__":
    main()
