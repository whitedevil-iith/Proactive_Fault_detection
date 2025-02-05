import subprocess
import json

def get_container_name(container_id):
    # Run the docker inspect command to get the container details in JSON format
    command = f"docker inspect {container_id}"
    try:
        # Get the output from the command and decode it
        output = subprocess.check_output(command, shell=True).decode()
        # Convert the output (JSON) to a Python object (list of dictionaries)
        container_info = json.loads(output)
        
        # Extract the container name from the first (and only) element in the list
        container_name = container_info[0]['Name']
        
        # Remove the leading '/' from the container name
        container_name = container_name.lstrip('/')
        
        return container_name
    except subprocess.CalledProcessError as e:
        print(f"Error while fetching container name: {e}")
        return None
    except json.JSONDecodeError as e:
        print(f"Error while parsing JSON output: {e}")
        return None

# Example usage
container_id = '4ed022dd71b1'
container_name = get_container_name(container_id)
if container_name:
    print(f"The container name for ID {container_id} is: {container_name}")
else:
    print("Could not retrieve container name.")
