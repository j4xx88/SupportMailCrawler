from .AbstractBaseClassLoader import AbstractBaseClassLoader

import requests
from bs4 import BeautifulSoup

from .AbstractBaseClassLoader import AbstractBaseClassLoader

class RequestsLoader(AbstractBaseClassLoader):

    headers = {
        'User-Agent': 'Mozilla/5.0 (X11; Fedora; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/70.0.3538.77 Safari/537.36'
    }

    def load_and_soup(target):
        text = ""
        try:
            resp = requests.get(target, allow_redirects=True, headers=RequestsLoader.headers)
            text = resp.text
        except Exception as e:
            print("exception")
            text = ""

        soup = BeautifulSoup(text, "lxml")
        return soup
