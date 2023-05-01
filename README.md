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

``sudo sysctl -p``

reload terminal and then run this command:

``ulimit -n 9999``