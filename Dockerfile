FROM python:3.7-slim-stretch

# Install your apt-get packages always like this to avoid cache problems
RUN apt-get update && apt-get install -y \
    supervisor nginx
RUN pip3 install --upgrade pip

COPY server_config/supervisord.conf /supervisord.conf
COPY server_config/nginx /etc/nginx/sites-available/default
COPY server_config/docker-entrypoint.sh /entrypoint.sh


COPY ./requirements.txt ./app/requirements.txt
# run this before the code, so that the packages
# are cached
RUN pip3 install -r ./app/requirements.txt

COPY . /app

RUN pip3 install -r ./app/requirements.txt

EXPOSE 9000 9001

ENTRYPOINT ["sh", "/entrypoint.sh"]
