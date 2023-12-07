FROM debian
RUN apt-get update && apt-get -y install python3 python3-flask python3-flask-babel python3-rpyc yt-dlp
RUN useradd -m user && sed -i 's/DEFAULT@SECLEVEL=2/DEFAULT@SECLEVEL=1/g' /etc/ssl/openssl.cnf
ADD --chown=user:user ripper /home/user/ripper
CMD ["su", "-c", "FLASK_APP=/home/user/ripper flask run --host=0.0.0.0 & rpyc_classic & wait", "user"]
