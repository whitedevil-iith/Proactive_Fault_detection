#!/bin/bash

# Docker installation 
for pkg in docker.io docker-doc docker-compose docker-compose-v2 podman-docker containerd runc; do sudo apt-get remove -y $pkg; done
# Add Docker's official GPG key:
sudo apt-get update
sudo apt-get install -y ca-certificates curl
sudo install -m 0755 -d /etc/apt/keyrings
sudo curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
sudo chmod a+r /etc/apt/keyrings/docker.asc

# Add the repository to Apt sources:
echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/ubuntu \
  $(. /etc/os-release && echo "$VERSION_CODENAME") stable" | \
  sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
sudo apt-get update

sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
sudo docker run hello-world
sudo groupadd docker
sudo usermod -aG docker $USER
#newgrp docker
#docker run hello-world
sudo systemctl enable docker.service
sudo systemctl enable containerd.service

# Define the base directory where the Dockerfiles are located
BASE_DIR="zmq"

# Function to build Docker image from Dockerfile in a specific folder
build_image() {
    IMAGE_NAME=$1
    DIR=$2

    echo "Building Docker image for ${IMAGE_NAME}..."
    docker build -t "$IMAGE_NAME" "$DIR"
    if [ $? -eq 0 ]; then
        echo "Successfully built image: ${IMAGE_NAME}"
    else
        echo "Failed to build image: ${IMAGE_NAME}"
    fi
}

# Build images for cu, du, and ue directories
for CU_DIR in "$BASE_DIR/cu"/*; do
    if [ -d "$CU_DIR" ]; then
        IMAGE_NAME=$(basename "$CU_DIR")
        build_image "$IMAGE_NAME" "$CU_DIR"
    fi
done

# Build DU and UE in parallel
for DIR in "$BASE_DIR/du" "$BASE_DIR/ue"; do
    if [ -d "$DIR" ]; then
        IMAGE_NAME=$(basename "$DIR")
        build_image "$IMAGE_NAME" "$DIR" &
    fi
done

echo "All images built successfully."

docker network create --subnet=10.0.0.0/8 oran-intel

git clone https://github.com/srsran/srsRAN_Project.git
cp -f setup/srsRAN_Project/docker-compose.yml srsRAN_Project/docker/
cp -f setup/srsRAN_Project/open5gs.env srsRAN_Project/docker/open5gs
cp -f setup/srsRAN_Project/subscriber_db.csv srsRAN_Project/docker/open5gs
cd srsRAN_Project/docker/open5gs/ && docker build --target open5gs -t open5gs-docker . && cd ../../..

git clone https://github.com/srsran/oran-sc-ric.git
cp -f setup/oran-sc-ric/docker-compose.yml oran-sc-ric/

cd oran-sc-ric && docker compose up

docker pull prom/prometheus:latest && docker run -d --name=prometheus --network=oran-intel -p 9090:9090 -v=$PWD/setup/prometheus-data:/prometheus-data prom/prometheus:latest --config.file=/prometheus-data/prometheus.yml
docker pull gcr.io/cadvisor/cadvisor:latest && docker run --name=cadvisor --network=oran-intel --volume=/:/rootfs:ro --volume=/var/run:/var/run:rw --volume=/sys:/sys:ro --volume=/var/lib/docker/:/var/lib/docker:ro --publish=8080:8080 --detach=true gcr.io/cadvisor/cadvisor:latest
docker run -d --name=node-exporter --network=oran-intel -p 9100:9100 prom/node-exporter:latest

cd srsRAN_Project/docker/open5gs/ && docker run -d --net oran-intel --ip 10.53.1.2 --name open5gs --env-file open5gs.env --privileged --publish 9999:9999 open5gs-docker ./build/tests/app/5gc -c open5gs-5gc.yml && cd ../../..

sleep 5

docker run -d -it --rm --privileged --cpus="3.0" --memory="2g" -v $PWD/zmq/cu/cu_0/cu.yml:/config/cu.conf --net oran-intel --ip 10.53.1.240 --name cu0 cu_0
docker run -d -it --rm --privileged --cpus="3.0" --memory="2g" -v $PWD/zmq/cu/cu_1/cu.yml:/config/cu.conf --net oran-intel --ip 10.53.1.140 --name cu1 cu_1
docker run -d -it --rm --privileged --cpus="3.0" --memory="2g" -v $PWD/zmq/cu/cu_2/cu.yml:/config/cu.conf --net oran-intel --ip 10.53.1.80 --name cu2 cu_2
docker run -d -it --rm --privileged --cpus="3.0" --memory="2g" -v $PWD/zmq/cu/cu_3/cu.yml:/config/cu.conf --net oran-intel --ip 10.53.1.90 --name cu3 cu_3

sleep 20 

sudo docker run -d -it --rm --privileged --cpus="3.0" --memory="3g" -v $PWD/zmq/du/du_zmq.conf:/config/du.conf --net oran-intel --ip 10.53.1.250 --name du0 du
sudo docker run -d -it --rm --privileged --cpus="3.0" --memory="3g" -v $PWD/zmq/du/du_zmq_1.conf:/config/du.conf --net oran-intel --ip 10.53.1.150 --name du1 du
sudo docker run -d -it --rm --privileged --cpus="3.0" --memory="3g" -v $PWD/zmq/du/du_zmq_2.conf:/config/du.conf --net oran-intel --ip 10.53.1.81 --name du2 du
sudo docker run -d -it --rm --privileged --cpus="3.0" --memory="3g" -v $PWD/zmq/du/du_zmq_3.conf:/config/du.conf --net oran-intel --ip 10.53.1.91 --name du3 du

sleep 5

sudo docker run -d -it --rm --privileged -v $PWD/zmq/ue/ue_zmq.conf:/configs/ue.conf -v $PWD/zmq/ue/tmp:/tmp --net oran-intel --ip 10.53.1.251 --name ue0 ue
sudo docker run -d -it --rm --privileged -v $PWD/zmq/ue/ue_zmq_1.conf:/configs/ue.conf -v $PWD/zmq/ue/tmp1:/tmp --net oran-intel --ip 10.53.1.151 --name ue1 ue
sudo docker run -d -it --rm --privileged -v $PWD/zmq/ue/ue_zmq_2.conf:/configs/ue.conf -v $PWD/zmq/ue/tmp2:/tmp --net oran-intel --ip 10.53.1.82 --name ue2 ue
sudo docker run -d -it --rm --privileged -v $PWD/zmq/ue/ue_zmq_3.conf:/configs/ue.conf -v $PWD/zmq/ue/tmp3:/tmp --net oran-intel --ip 10.53.1.92 --name ue3 ue

cd srsRAN_Project && sudo docker compose -f docker/docker-compose.yml up grafana

echo "Setup complete. Some components are running in separate terminals."
