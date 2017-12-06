from aiohttp import web

from etc.config import NGW_HOST, NGW_PASSWORD, NGW_LOGIN
from ngw.api_crud import CrudHandler
from ngw.api_view import ViewHandler


crudHandler = CrudHandler(NGW_HOST, NGW_LOGIN, NGW_PASSWORD)
viewHandler = ViewHandler(NGW_HOST, NGW_LOGIN, NGW_PASSWORD)

app = web.Application(client_max_size=10*1024*1024)
app.router.add_post('/save', crudHandler.save)

app.router.add_get(r'/{map:\d+}/MapServer', viewHandler.index)
app.router.add_get(r'/{map:\d+}/MapServer/{id_layer:\d+}', viewHandler.layer_info)
app.router.add_get(r'/{map:\d+}/MapServer/export', viewHandler.export)
app.router.add_get(r'/{map:\d+}/MapServer/layers', viewHandler.layers)
app.router.add_get(r'/{map:\d+}/MapServer/identify', viewHandler.identify)
