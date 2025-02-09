import json
import requests
from requests.adapters import HTTPAdapter, Retry


# Requests to the alerts server may be patchy at times, incorporate a retry interface with exponential backoff
class RequestWithRetry:
    def __init__(self, retries=3):
        self.retries = Retry(total=retries, backoff_factor=0.1, status_forcelist=[500, 502, 503, 504])

    def request_with_retry(self, url, method='get', body=None):
        s = requests.Session()
        s.mount('http://', HTTPAdapter(max_retries=self.retries))
        if method == 'get':
            return s.get(url)
        elif method == 'post':
            return s.post(url, body)
        else:
            raise TypeError("invalid request method - {}, only 'get' or 'post' allowed".format(method))


class Client:
    def __init__(self, address):
        if address == "":
            address = "http://127.0.0.1:9001"
        self.address = address
        self.http_client = RequestWithRetry(3)

    def query_alerts(self):
        url = self.address + "/alerts"
        response = self.http_client.request_with_retry(url)
        if response.status_code != 200:
            raise ConnectionError("could not complete request got " + str(response.status_code))
        return response.json()

    def notify(self, alertname, message):
        url = self.address + "/notify"
        request = {
            "alertName": alertname,
            "message": message
        }
        response = self.http_client.request_with_retry(url, 'post', json.dumps(request))
        if response.status_code != 200:
            raise ConnectionError("could not complete request got " + str(response.status_code))

    def resolve(self, alertname):
        url = self.address + "/resolve"
        request = {
            "alertName": alertname
        }
        response = self.http_client.request_with_retry(url, 'post', json.dumps(request))
        if response.status_code != 200:
            raise ConnectionError("could not complete request got " + str(response.status_code))

    def query(self, target):
        url = self.address + "/query?target=" + target
        response = self.http_client.request_with_retry(url)
        if response.status_code != 200:
            raise ConnectionError("could not complete request got " + str(response.status_code))
        return response.json()["value"]
