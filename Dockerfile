FROM debian:testing
RUN apt-get update && apt-get -y install python3 python3-flask python3-flask-babel python3-rpyc python3-werkzeug yt-dlp
RUN useradd -m user
ADD --chown=user:user ripper /home/user/ripper
CMD ["su", "-c", "FLASK_APP=/home/user/ripper flask run --host=0.0.0.0 & rpyc_classic & wait", "user"]
