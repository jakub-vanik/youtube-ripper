# youtube-ripper
This application is a simple web based frontend for [yt-dlp](https://github.com/yt-dlp/yt-dlp). It is designed to be run inside Docker container. The application consist of background Python service which downloads streams using yt-dlp and [Flask](https://www.palletsprojects.com/p/flask/) web application which provides user interface. These two parts communicate by [RPyC](https://rpyc.readthedocs.io/en/latest/). Background service is started by web application when needed and terminates itself when there is no more work. Download requests are served one each time. Video is downloaded from stream service to the server which runs this application. Than link is shown to user for downloading video from the server. Meanwhile next video download may already start. Video is deleted after one hour from the server. Users can see whole download queue. But each user is able to download only videos he requested. Also names and source URLs of other users' videos are hidden.

## Deployment
Application can be deployed as standalone web or as a part of other web at some path. In following code snippets path **/ripper/** is used.

### Common part
- Generate your own **SECRET_KEY**.

   Replace the **SECRET_KEY** in file **ripper/config.json** by output of following command.

```
python -c 'import secrets; print(secrets.token_hex())'
```

- Build image using provided Dockerfile.
```
docker build -t ripper .
```

### Standalone web
- Create container and start it in background.
```
docker run -d -p 80:5000 --restart always --name ripper ripper
```

### Part of other web
- Create container and start it in background.
```
docker run -d --restart always --name ripper ripper
```

- Setup webserver to proxy requests to the application.

   [Proxy Fix](https://werkzeug.palletsprojects.com/en/3.0.x/middleware/proxy_fix/) form Werkzeug is used to allow run application behind reverse proxy.

   **X-Forwarded-Prefix** header must be set to base path at which is application accessed.

   Following configuration snippet can be used if NGINX is used:

```
location /ripper/ {
    proxy_pass http://172.17.0.2/;
    proxy_set_header X-Forwarded-Prefix /ripper/;
}
```

## Configuration
Service shuts down after one hour of inactivity. Downloaded files are deleted one hour after download finishes. Both these times can be changed near the top of **ripper/service.py** where **service_timeout** and **download_timeout** are set.
