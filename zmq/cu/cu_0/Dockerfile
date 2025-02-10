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
    tcpdump \
    net-tools \
    inetutils-tools \
    libgtest-dev \
    libyaml-cpp-dev \
    && rm -rf /var/lib/apt/lists/*




# Build and install GTest from source
RUN cd /usr/src/gtest && \
    cmake . && \
    make -j$(nproc) && \
    mv lib/*.a /usr/lib

RUN apt-get install libzmq3-dev

RUN git clone https://github.com/zeromq/czmq.git /opt/czmq

WORKDIR /opt/czmq
RUN ./autogen.sh && \
    ./configure && \
    make && \
    make install && \
    ldconfig

# Clone the srsRAN repository
RUN git clone https://github.com/srsRAN/srsRAN_Project.git /opt/srsRAN_Project

# Build and install srsRAN
WORKDIR /opt/srsRAN_Project
RUN git checkout e5d5b44b9 && \
    mkdir build && cd build && \
    cmake -DDU_SPLIT_TYPE=SPLIT_8 ../ -DENABLE_EXPORT=ON -DENABLE_ZEROMQ=ON && \
    make -j$(nproc) && \
    make test -j$(nproc) || true && \
    make install && \
    apt-get purge -y --auto-remove build-essential cmake make && \
    apt-get clean && rm -rf /var/lib/apt/lists/* /tmp/*



# Set working directory for configuration
WORKDIR /config

# Add the entrypoint script
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

# Set entrypoint and default command
ENTRYPOINT ["/entrypoint.sh"]

# Command to run srsDU with the provided configuration file
CMD ["srscu", "-c", "/config/cu.conf"]

#sudo docker run -it --rm --privileged -v /home/yaswanth/Desktop/Education/twin/cu/cu.yml:/config/cu.conf --net open5gsnet --ip 10.53.1.240 srs_cu_zmq

