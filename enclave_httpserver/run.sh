#!/bin/sh

# Assign an IP address to local loopback 
ip addr add 127.0.0.1/32 dev lo

ip link set dev lo up

/enclave_httpserver &
socat VSOCK-LISTEN:8001,fork,reuseaddr TCP:127.0.0.1:8888
