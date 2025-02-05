cd srsRAN_Project/docker/open5gs/ && docker run -d --net oran-intel --ip 10.53.1.2 --name open5gs --env-file open5gs.env --privileged --publish 9999:9999 open5gs-docker ./build/tests/app/5gc -c open5gs-5gc.yml && cd ../../..

sleep 5

docker run -d -it --rm --privileged --cpus="2.0" --memory="2g" -v $PWD/zmq/cu/cu_0/cu.yml:/config/cu.conf --net oran-intel --ip 10.53.1.240 --name cu0 cu_0
docker run -d -it --rm --privileged --cpus="2.0" --memory="2g" -v $PWD/zmq/cu/cu_1/cu.yml:/config/cu.conf --net oran-intel --ip 10.53.1.140 --name cu1 cu_1
docker run -d -it --rm --privileged --cpus="2.0" --memory="2g" -v $PWD/zmq/cu/cu_2/cu.yml:/config/cu.conf --net oran-intel --ip 10.53.1.80 --name cu2 cu_2
docker run -d -it --rm --privileged --cpus="2.0" --memory="2g" -v $PWD/zmq/cu/cu_3/cu.yml:/config/cu.conf --net oran-intel --ip 10.53.1.90 --name cu3 cu_3

sleep 5 

sudo docker run -d -it --rm --privileged --cpus="3.0" --memory="3g" -v $PWD/zmq/du/du_zmq.conf:/config/du.conf --net oran-intel --ip 10.53.1.250 --name du0 du
sudo docker run -d -it --rm --privileged --cpus="3.0" --memory="3g" -v $PWD/zmq/du/du_zmq_1.conf:/config/du.conf --net oran-intel --ip 10.53.1.150 --name du1 du
sudo docker run -d -it --rm --privileged --cpus="3.0" --memory="3g" -v $PWD/zmq/du/du_zmq_2.conf:/config/du.conf --net oran-intel --ip 10.53.1.81 --name du2 du
sudo docker run -d -it --rm --privileged --cpus="3.0" --memory="3g" -v $PWD/zmq/du/du_zmq_3.conf:/config/du.conf --net oran-intel --ip 10.53.1.91 --name du3 du

sleep 10

sudo docker run -d -it --rm --privileged -v $PWD/zmq/ue/ue_zmq.conf:/configs/ue.conf -v $PWD/zmq/ue/tmp:/tmp --net oran-intel --ip 10.53.1.251 --name ue0 ue
sudo docker run -d -it --rm --privileged -v $PWD/zmq/ue/ue_zmq_1.conf:/configs/ue.conf -v $PWD/zmq/ue/tmp1:/tmp --net oran-intel --ip 10.53.1.151 --name ue1 ue
sudo docker run -d -it --rm --privileged -v $PWD/zmq/ue/ue_zmq_2.conf:/configs/ue.conf -v $PWD/zmq/ue/tmp2:/tmp --net oran-intel --ip 10.53.1.82 --name ue2 ue
sudo docker run -d -it --rm --privileged -v $PWD/zmq/ue/ue_zmq_3.conf:/configs/ue.conf -v $PWD/zmq/ue/tmp3:/tmp --net oran-intel --ip 10.53.1.92 --name ue3 ue
