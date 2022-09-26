FROM python:3.8.1-slim

COPY ./*.py ./*.sh ./*.txt /app/
RUN pip install -U pip && pip install -r /app/requirements.txt

WORKDIR /app/

RUN useradd demo
RUN chown demo /app/
USER demo

EXPOSE 4747

ENTRYPOINT ["bash", "/app/run-prod.sh"]