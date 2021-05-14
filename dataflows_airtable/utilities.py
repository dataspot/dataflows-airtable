import os
import time
import requests


class RateLimiter():
    def __init__(self, delay=0.2):
        self.delay = delay
        self.last = None

    def execute(self, func):
        curtime = time.time()
        if self.last is not None and curtime - self.last < self.delay:
            time.sleep(self.delay - (curtime - self.last))
        self.last = time.time()
        return func()

rate_limiter = RateLimiter()


def get_session(apikey):
    if apikey.startswith('env://'):
        apikey = apikey[6:]
        apikey = os.environ[apikey]
    session = requests.Session()
    session.headers = dict(Authorization=f'Bearer {apikey}')
    return session
