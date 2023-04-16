#!/bin/bash
#git clone https://github.com/flslab/SwarMer.git
#cd SwarMer
#git branch feature_lease

sudo apt update
sudo apt install python3-pip
pip3 install -r requirements.txt
echo "now run python3 server.py"
