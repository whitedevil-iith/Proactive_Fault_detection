# Base image
FROM ubuntu:22.04

# Set non-interactive mode
ENV DEBIAN_FRONTEND=noninteractive

# Install required packages
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
    ccache \
    make \
    gcc \
    g++ \
    pkg-config \
    libboost-all-dev \
    libfftw3-dev \
    libmbedtls-dev \
    libboost-program-options-dev \
    libconfig++-dev \
    libsctp-dev \
    autoconf \
    libtool \
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
    inetutils-tools \
    libgtest-dev \
    libyaml-cpp-dev \
    && rm -rf /var/lib/apt/lists/*

# Add Ettus Research UHD repository and install UHD packages
RUN sudo add-apt-repository ppa:ettusresearch/uhd && \
    apt-get update && \
    apt-get install -y libuhd-dev uhd-host

# ZMQ installation (Conditional)
# Uncomment these lines if ZMQ support is required
RUN git clone https://github.com/zeromq/libzmq.git /opt/libzmq && \
    cd /opt/libzmq && \
    ./autogen.sh && \
    ./configure && \
    make -j$(nproc) && \
    make install && \
    ldconfig && \
    cd / && rm -rf /opt/libzmq
RUN git clone https://github.com/zeromq/czmq.git /opt/czmq && \
    cd /opt/czmq && \
    ./autogen.sh && \
    ./configure && \
    make -j$(nproc) && \
    make install && \
    ldconfig && \
    cd / && rm -rf /opt/czmq

# Build and install GTest from source
RUN cd /usr/src/gtest && \
    cmake . && \
    make -j$(nproc) && \
    mv lib/*.a /usr/lib

# Clone the srsRAN repository
RUN git clone https://github.com/srsRAN/srsRAN_Project.git /opt/srsRAN_Project && \
    cd /opt/srsRAN_Project && \
    git checkout release_24_10

# Build and install srsRAN
WORKDIR /opt/srsRAN_Project
RUN git checkout release_23_10 && \
    mkdir build && cd build && \
    # Uncomment the following line if using ZMQ
    cmake ../ -DDU_SPLIT_TYPE=SPLIT_8 -DENABLE_EXPORT=ON -DENABLE_ZEROMQ=ON && \
    # Use this line if not using ZMQ
    #cmake ../ -DDU_SPLIT_TYPE=SPLIT_8 && \
    make -j$(nproc) && \
    make test -j$(nproc) || true && \
    make install && \
    apt-get purge -y --auto-remove build-essential cmake make && \
    apt-get clean && rm -rf /var/lib/apt/lists/* /tmp/*

# Download UHD images
RUN python3 /lib/uhd/utils/uhd_images_downloader.py && \
    export UHD_IMAGES_DIR=/usr/share/uhd/images

# Set environment variable for UHD images
ENV UHD_IMAGES_DIR=/usr/share/uhd/images

# Set working directory for configuration
# WORKDIR /config

# Command to run srsDU with the provided configuration file
CMD ["srsdu", "-c", "/config/du.conf"]

# Example run command (commented for documentation purposes): while using uhd
# sudo docker run -it --rm --privileged --device=/dev/bus/usb/002/004 -v /home/yaswanth/Desktop/Education/twin/du/du.yaml:/config/du.conf --net open5gsnet --ip 10.53.1.250 du

#while using zmq
#sudo docker run -it --rm --privileged -v /home/yaswanth/Desktop/Education/twin/du/du.yaml:/config/du.conf --net open5gsnet --ip 10.53.1.250 du_zmq 
