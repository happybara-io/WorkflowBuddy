FROM python:3.10.7-slim

# inspired by Noco-DB https://github.com/nocodb/nocodb/blob/develop/packages/nocodb/Dockerfile
ENV WB_DATA_DIR=/usr/app/data/
ENV ENV=PROD

WORKDIR /usr/src/app/
COPY requirements.txt ./requirements.txt
RUN mkdir -p /usr/app/data/ && pip install -U pip && pip install -r ./requirements.txt
ADD buddy ./buddy
COPY ./*.py ./*.sh .

RUN useradd demo && chown demo /usr/app/data/
# RUN chown demo /usr/src/app/
USER demo

EXPOSE 4747

ENTRYPOINT ["bash", "/usr/src/app/run-prod.sh"]
