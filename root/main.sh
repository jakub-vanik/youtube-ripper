#!/bin/sh

export FLASK_APP=/srv/http/ripper
su -s /bin/bash -c "flask run & rpyc_classic.py &" -g www-data www-data
nginx -c /root/nginx.conf
