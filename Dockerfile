FROM python:3.10.7-slim

COPY requirements.txt /app/requirements.txt
RUN pip install -U pip && pip install -r /app/requirements.txt
COPY ./*.py ./*.sh /app/
WORKDIR /app/

RUN useradd demo
RUN chown demo /app/
USER demo

EXPOSE 4747

ENTRYPOINT ["bash", "/app/run-prod.sh"]