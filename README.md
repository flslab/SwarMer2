# SwarMer

## Clone
``git clone https://github.com/flslab/SwarMer.git``

## Setup

``bash setup.sh``

## Large Point Clouds
Increase max open files system-wide to be able to run a large point cloud:

``sudo vim /etc/sysctl.conf``

Add the following line:

``fs.file-max = 2097152``

reload terminal and then run these command:

``sudo sysctl -p``
``ulimit -n 4096``