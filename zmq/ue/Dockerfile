# Use Ubuntu 20.04 as the base image
FROM ubuntu:20.04

# Set environment variables to prevent interactive prompts during package installation
ENV DEBIAN_FRONTEND=noninteractive
ENV UHD_IMAGES_DIR=/usr/share/uhd/images

# Update and install general prerequisites, including the additional packages you requested
RUN apt-get update && apt-get install -y \
    software-properties-common \
    sudo \
    nano \
    iproute2 \
    iputils-ping \
    wget \
    gnupg \
    build-essential \
    cmake \
    git \
    libboost-all-dev \
    libfftw3-dev \
    libmbedtls-dev \
    libboost-program-options-dev \
    libconfig++-dev \
    libsctp-dev \
    autoconf \
    libtool \
    pkg-config \
    libzmq3-dev \
    libusb-1.0-0 \
    libusb-1.0-0-dev \
    libusb-dev \
    python3 \
    python3-pip \
    python3-dev \
    python3-mako \
    python3-numpy \
    python3-requests \
    python3-scipy \
    python3-setuptools \
    python3-ruamel.yaml \
    ethtool \
    cpufrequtils \
    doxygen \
    g++ \
    inetutils-tools \
    ccache \
    iperf3 \
    && apt-get clean

#uncomment this if zmq enabled
RUN apt-get install libzmq3-dev

RUN add-apt-repository ppa:srslte/releases\
    && apt-get update

RUN apt-get install -y srsue uhd-host \
    && apt-get clean

# Install LTS version of UHD (3.9.7 or 3.15 recommended)
RUN git clone https://github.com/EttusResearch/uhd.git \
    && cd uhd \
    && git checkout UHD-4.7 \
    && cd host \
    && mkdir build \
    && cd build \
    && cmake ../ \
    && make -j$(nproc) \
    && mkdir -p /usr/share/uhd/images \
    && make install \
    && ldconfig \
    && cd ../.. \
    && rm -rf uhd

RUN /usr/lib/uhd/utils/uhd_images_downloader.py


# Clone and build srsRAN_4G from source
RUN git clone https://github.com/srsRAN/srsRAN_4G.git /tmp/srsRAN_4G \
    && cd /tmp/srsRAN_4G \
    && mkdir build \
    && cd build \
    #uncomment the below line if using zmq
    && cmake ../ -DENABLE_RF_PLUGINS=OFF \
    #uncomment below line when using uhd
    #&& cmake ../ \
    && make -j$(nproc) \
    && make install \
    && ldconfig \
    && srsran_install_configs.sh user \
    && rm -rf /tmp/srsRAN_4G

# Set UHD environment variables for runtime
ENV PATH="/usr/lib/uhd/utils:$PATH"

# Default command to run srsUE with the ue.conf file
WORKDIR /usr/bin
CMD ["srsue", "/configs/ue.conf"]

#use below while using uhd
# sudo docker run --privileged -it -v /home/yaswanth/Desktop/Education/twin/ue/ue.conf:/usr/bin/ue.conf --device=/dev/bus/usb/002/002:/dev/bus/usb/002/002 srsue

#while using zmq use this
#sudo docker run -it --rm --privileged -v /home/yaswanth/Desktop/Education/twin/ue/ue.conf:/config/ue.conf --net open5gsnet --ip 10.53.1.251 srsue_zmq