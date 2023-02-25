FROM python:3.10.7-slim

# inspired by Noco-DB https://github.com/nocodb/nocodb/blob/develop/packages/nocodb/Dockerfile
ENV WB_DATA_DIR=/usr/app/data/
ENV APP_DIR=/usr/src/app/
ENV ENV=PROD
ENV DB_TYPE='sqlite'

WORKDIR ${APP_DIR}
COPY requirements.txt ./requirements.txt
RUN mkdir -p "${WB_DATA_DIR}" && pip install -U pip && pip install -r ./requirements.txt
ADD buddy ./buddy
COPY ./*.py ./*.sh "${APP_DIR}"

RUN useradd demo && chown demo "${WB_DATA_DIR}"
# RUN chown demo /usr/src/app/
USER demo

EXPOSE 4747

ENTRYPOINT ["bash", "/usr/src/app/run-prod.sh"]
