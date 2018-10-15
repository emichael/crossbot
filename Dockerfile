FROM python:3.6-alpine

WORKDIR /crossbot

# matplotlib, numpy require these
RUN apk add --no-cache \
  pkgconfig \
  build-base \
  freetype-dev \
  libpng-dev \
  openblas-dev

# Install the other dependencies
RUN apk add --no-cache \
  nginx \
  sqlite \
  supervisor

RUN pip3 install gunicorn

# Install crossbot custom dependencies
COPY ./requirements.txt ./
RUN pip3 install --no-cache-dir -r requirements.txt

# Now, copy over the full application
COPY ./crossbot ./crossbot
COPY ./manage.py ./settings.py ./setup.py ./urls.py ./wsgi.py ./

# create a directory to be mapped to the host which will store the database
VOLUME ["/crossbot/db", "/crossbot/secrets"]
RUN ln -s secrets/keys.py keys.py
RUN ln -s db/crossbot.db crossbot.db

# Configure nginx to not run as a daemon
RUN echo "daemon off;" >> /etc/nginx/nginx.conf

# Add missing folder to make nginx work
RUN mkdir -p /run/nginx

# Configure nginx to serve crossbot
RUN echo $'\
server { \n\
   listen 80; \n\
    location = /favicon.ico { \n\
      access_log off; \n\
      log_not_found off; \n\
    } \n\
    location /static/ { \n\
        alias /crossbot/static/; \n\
    } \n\
    location / { \n\
        proxy_pass http://unix:/crossbot-app.sock; \n\
    } \n\
} \n\
' > /etc/nginx/conf.d/crossbot.conf

# Get rid of the default server
RUN rm /etc/nginx/conf.d/default.conf

# Configure supervisor to start nginx and gunicorn
RUN mkdir -p /etc/supervisor.d/
RUN echo $'\
[supervisord] \n\
nodaemon=true \n\
\n\
[program:gunicorn] \n\
command=sh -c "/crossbot/manage.py migrate --fake-initial; /crossbot/manage.py collectstatic; gunicorn -w 4 --chdir /crossbot wsgi:application --bind unix:/crossbot-app.sock" \n\
\n\
[program:nginx] \n\
command=nginx \n\
' > /etc/supervisor.d/crossbot.ini

CMD ["/usr/bin/supervisord"]


EXPOSE 80
