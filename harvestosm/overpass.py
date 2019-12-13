import requests


class Overpass:
    # defaults for Overpass class
    _endpoint = "https://overpass-api.de/api/interpreter"
    _headers = {"Accept-Charset": "utf-8;q=0.7,*;q=0.7"}
    _timeout = 25  # seconds
    _proxies = None

    def __init__(self, query, *args, **kwargs):
        self.endpoint = kwargs.get("endpoint", self._endpoint)
        self.headers = kwargs.get("headers", self._headers)
        self.timeout = kwargs.get("timeout", self._timeout)
        self.proxies = kwargs.get("proxies", self._proxies)
        self._status = None
        self.query = query

    @property
    def get_from_overpass(self):
        payload = {"data": self.query}

        try:
            response = requests.post(
                self.endpoint,
                data=payload,
                timeout=self.timeout,
                proxies=self.proxies,
                headers=self.headers,
            )

        except requests.exceptions.Timeout:
            raise TimeoutError(self._timeout)

        self._status = response.status_code

        if self._status != 200:
            if self._status == 400:
                # raise OverpassSyntaxError(query)
                print('Overpass Syntax Error')
            elif self._status == 429:
                # raise MultipleRequestsError()
                print('Multiple Requests Error')
            elif self._status == 504:
                # raise ServerLoadError(self._timeout)
                print('Server Load Error')
            else:
                print(f'The request returned status code {self._status}')
        else:
            response.encoding = "utf-8"
            return response