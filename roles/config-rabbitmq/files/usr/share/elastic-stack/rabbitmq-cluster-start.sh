#!/bin/bash

# Run your process in background
python3 /usr/share/elastic-stack/rabbitmq-cluster.py -a start -s 1 &
# Check if the services started successfully 
if ! kill -0 $! 2>/dev/null; then
    # Return 1 so that systemd knows the service failed to start
    exit 1
fi
