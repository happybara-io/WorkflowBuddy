import logging
import requests


def send_webhook(url, json_body):
    resp = requests.post(url, json=json_body)
    logging.info(f"{resp.status_code}: {resp.text}")
    return resp
