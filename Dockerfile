FROM curlimages/curl:latest AS fetch
WORKDIR /usr/src/
# This is a fat file of 100+MB, probably want a better plan here
RUN curl http://get.nocodb.com/linux-x64 -o nocodb -L && chmod +x nocodb

FROM python:3.10.7-slim

# inspired by Noco-DB https://github.com/nocodb/nocodb/blob/develop/packages/nocodb/Dockerfile
ENV WB_DATA_DIR=/usr/app/data/
ENV ENV=PROD
ENV DB_TYPE='sqlite'
ENV NC_DISABLE_TELE=true
ENV NC_MIN=true
ENV NC_DB='sqlite3://sqlite3?d=/usr/app/data/noco.db'

WORKDIR /usr/src/app/
COPY --from=fetch /usr/src/nocodb ./
COPY requirements.txt ./requirements.txt
RUN mkdir -p /usr/app/data/; pip install -U pip && pip install -r ./requirements.txt
ADD buddy ./buddy
COPY ./*.py ./*.sh /usr/src/app/

RUN useradd demo && chown demo /usr/app/data/
# RUN chown demo /usr/src/app/
USER demo

EXPOSE 4747 8080

ENTRYPOINT ["bash", "/usr/src/app/run-prod.sh"]
