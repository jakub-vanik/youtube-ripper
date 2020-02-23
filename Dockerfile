FROM debian:buster
WORKDIR /root
RUN apt-get update && apt-get -y install nginx ffmpeg python3 python3-pip
RUN pip3 --no-cache-dir install Flask Flask-Babel rpyc youtube_dl
RUN sed -i 's/DEFAULT@SECLEVEL=2/DEFAULT@SECLEVEL=1/g' /etc/ssl/openssl.cnf
ADD root /root
ADD http /srv/http
CMD ["sh", "main.sh"]
