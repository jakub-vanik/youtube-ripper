# youtube-ripper
This application is a simple web based frontend for [youtube-dl](https://github.com/ytdl-org/youtube-dl). It is designed to be run inside Docker container together with [NGINX](https://www.nginx.com/) which allows user to download ripped video. The application consist of background Python service which downloads streams using youtube-dl and [Flask](https://www.palletsprojects.com/p/flask/) web application which provides user interface. These two parts communicate by [RPyC](https://rpyc.readthedocs.io/en/latest/). Background service is started by web application when needed and terminates itself when there is no more work. Download requests are served one each time. Video is downloaded from stream service to the server which runs this application. Than link is shown to user for downloading video from the server. Meanwhile next video download may already start. Video is deleted after one hour from the server. Users can see whole download queue. But each user is able to download only videos he requested. Also names and source URLs of other users' videos are hidden.

## Deployment
Application can be deployed as standalone web or as a part of other web at some path. In following code snippets path **/ripper/** is used.

### Common part
- Create work directory.
```
mkdir http/output
chmod 0777 http/output
```

- Generate your own **SECRET_KEY**.

   Replace constant at line **25** in file **http/ripper/\_\_init\_\_.py** by output of following command.

```
python -c 'import os; print(os.urandom(16))'
```

- Build image using provided Dockerfile.
```
docker build -t ripper .
```

### Standalone web
- Create container and start it in background.
```
docker run -d -p 80:80 --restart always --name ripper ripper
```

### Part of other web
- Create container and start it in background.

   **SCRIPT_NAME** is base path excluding domain used by flask for link generation.

```
docker run -d -e 'SCRIPT_NAME=/ripper/' --restart always --name ripper ripper
```

- Setup webserver to proxy requests to the application.

   **Host** header must be forwarded. **X-Forwarded-Proto** header must be set if HTTPS scheme is used.

   Following configuration snippet can be used if NGINX is used:

```
location /robodj/ {
    proxy_pass http://172.17.0.2/;
    proxy_set_header Host $host;
    proxy_set_header X-Forwarded-Proto $scheme;
    proxy_read_timeout 300s;
}
```

## Configuration
Download speed is limited to 512 kB. Download speed for youtube-dl can be changed in **http/ripper/service.py** where **ratelimit** parameter is set. Download speed for NGINX can be changed in **root/nginx.conf** where **limit_rate** parameter is set.

Service shuts down after one hour of inactivity. Downloaded files are deleted one hour after download finishes. Both these times can be changed near the top of **http/ripper/service.py** where **service_timeout** and **download_timeout** are set.
