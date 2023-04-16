#!/bin/bash
sudo apt update
sudo apt install python3-pip
pip3 install -r requirements.txt
git branch feature_lease
echo "now run python3 server.py"
