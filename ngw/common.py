import requests


class NGWException(Exception):
    pass


class NGW:
    def __init__(self, host, username, password):
        self._session = requests.session()
        self._session.headers = {
            'Accept': '*/*',
        }

        self._host = host
        self._username = username
        self._password = password

        self._api = {
            'login': 'login',
            'info': 'api/resource/{resource_p}',
            'create': 'api/resource/{layer_p}/feature/',
            'edit': 'api/resource/{layer_p}/feature/{feature_p}',
            'render': 'api/component/render/image',
            'identify': 'feature_layer/identify',
        }

    @property
    def _is_auth(self):
        self._session.cookies.clear_expired_cookies()
        if self._session.cookies.get('tkt') is None:
            return False
        return True

    def _ngw_auth(self):
        auth_response = self._session.post(
            f'{self._host}/{self._api["login"]}',
            data={
                'login': self._username,
                'password': self._password
            }
        )

        if auth_response.status_code != 200:
            raise NGWException('Authenticated failed')

    def _ngw_info(self, resource_id):
        if not self._is_auth:
            self._ngw_auth()

        uri = self._api['info'].format(resource_p=resource_id)
        info_response = self._session.get(f'{self._host}/{uri}')

        if info_response.status_code != 200:
            raise NGWException('Resource not found')

        return info_response.json()
