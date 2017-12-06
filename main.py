from aiohttp import web

from uwsgi import app

# Run debug or run without gunicorn/uwsgi e.t.c
if __name__ == '__main__':
    web.run_app(app, port=8000)
