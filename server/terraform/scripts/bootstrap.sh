#!/bin/bash

git clone https://github.com/irdan/crypto-workshop.git
cd crypto-workshop/server

sudo apt install -y python-pip
pip install -r requirements.txt
sh find_ip.sh

sudo cp ~/crypto-workshop/server/*.service /etc/systemd/system/.

sudo systemctl enable hashing.service
sudo systemctl enable pki.service

sudo chmod +x /home/dantheman/crypto-workshop/server/pki-server.py
sudo chmod +x /home/dantheman/crypto-workshop/server/hashing-server.py

sudo systemctl start hashing
sudo systemctl start pki

sudo systemctl is-active pki.service && sudo systemctl is-active hashing.service
