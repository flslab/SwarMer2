#!/bin/bash
sudo apt update -y
if ! command -v pip3 &> /dev/null
then
    echo "pip3 could not be found"
    echo "installing pip3 ..."
    sudo apt install python3-pip -y
fi
pip3 install -r requirements.txt
echo "now run python3 server.py"