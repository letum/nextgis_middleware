import json
import re
from aiohttp import web
from math import fabs
from osgeo import ogr

from ngw.common import NGW, NGWException


class ViewHandler(NGW):
    def __init__(self, host, username, password):
        super().__init__(host, username, password)

    async def export(self, request):
        if not self._is_auth:
            try:
                self._ngw_auth()

            except NGWException as ex:
                return web.json_response({
                    'error': str(ex),
                })

        layers_set = request.query.get('layers', '')
        layers_id = re.search('\w+:([\d,]+)', layers_set)
        if layers_id is None:
            raise web.HTTPBadRequest()

        else:
            style_list = layers_id.group(1)

        request_params = {
            'extent': request.query.get('bbox'),
            'size': request.query.get('size'),
            'resource': style_list,
        }

        image = self._session.get(
            f'{self._host}/{self._api["render"]}',
            params=request_params,
            stream=True
        )

        return web.Response(body=image.raw, content_type='image/png')

    async def index(self, request):
        id_map = request.match_info['map']
        try:
            map_info = self._ngw_info(id_map)

        except NGWException as ex:
            return web.json_response({
                'error': str(ex),
            })

        styles = []
        for child in map_info['webmap']['root_item']['children']:
            styles.append({
                'id': child['layer_style_id'],
                'name': child['display_name'],
                'maxScale': child['layer_max_scale_denom'],
                'minScale': child['layer_min_scale_denom'],
                'defaultVisibility': child['layer_enabled'],
            })

        json_data = {
            'copyrightText': map_info['resource']['display_name'],
            'currentVersion': 10.2,
            'capabilities': 'Map,Query,Data',
            'mapName': 'Layers',
            'description': '',
            'spatialReference': {
                'wkid': 28417,
            },
            'supportsDynamicLayers': True,
            'exportTilesAllowed': False,
            'units': "esriDecimalDegrees",
            'supportedQueryFormats': 'JSON,AMF',
            'supportedImageFormatTypes': 'PNG32,PNG24,PNG,JPG,DIB,TIFF,EMF,PS,PDF,GIF,SVG,SVGZ,BMP',
            'layers': styles,
            'tables': []
        }
        json_str = json.dumps(json_data)

        callback = request.query.get('callback', '')
        return web.Response(body=f'{callback}({json_str})')

    async def layers(self, request):
        id_map = request.match_info['map']
        try:
            map_info = self._ngw_info(id_map)

        except NGWException as ex:
            return web.json_response({
                'error': str(ex),
            })

        styles = []
        for child in map_info['webmap']['root_item']['children']:
            styles.append({
                'id': child['layer_style_id'],
                'name': child['display_name'],
                'maxScale': child['layer_max_scale_denom'],
                'minScale': child['layer_min_scale_denom'],
                'defaultVisibility': child['layer_enabled'],
            })

        json_data = {
            'layers': styles,
            'tables': [],
        }
        json_str = json.dumps(json_data)

        callback = request.query.get('callback', '')
        return web.Response(body=f'{callback}({json_str})')

    async def identify(self, request):
        if not self._is_auth:
            try:
                self._ngw_auth()

            except NGWException as ex:
                return web.json_response({
                    'error': str(ex),
                })

        try:
            extent = request.query.get('mapExtent', '').split(',')
            image_display = request.query.get('imageDisplay', '').split(',')
            tolerance = float(request.query.get('tolerance', '3'))
            point = json.loads(request.query.get('geometry'))

            layers_set = request.query.get('layers', '')
            styles_id = re.search('\w+:([\d,]+)', layers_set)
            if len(extent) != 4 or len(image_display) != 3 or styles_id is None or point is None:
                raise web.HTTPBadRequest()

        except (ValueError, AttributeError):
            raise web.HTTPBadRequest()

        # Calculate map coefficients
        extent_point = tuple(map(float, extent))
        map_weight = fabs(extent_point[2] - extent_point[0])
        map_height = fabs(extent_point[3] - extent_point[1])

        map_container = tuple(map(float, image_display))
        weight_coef = (map_weight / map_container[0]) * tolerance
        height_coef = (map_height / map_container[1]) * tolerance

        # Create ring
        ring = ogr.Geometry(ogr.wkbLinearRing)
        ring.AddPoint(point['x'] - weight_coef, point['y'] - height_coef)
        ring.AddPoint(point['x'] - weight_coef, point['y'] + height_coef)
        ring.AddPoint(point['x'] + weight_coef, point['y'] + height_coef)
        ring.AddPoint(point['x'] + weight_coef, point['y'] - height_coef)
        ring.AddPoint(point['x'] - weight_coef, point['y'] - height_coef)

        # Create polygon
        polygon = ogr.Geometry(ogr.wkbPolygon)
        polygon.AddGeometry(ring)

        # Get layers ID by style ID
        layers = []
        for style in styles_id.group(1).split(','):
            style_info = self._ngw_info(style)
            layers.append(style_info['resource']['parent']['id'])

        request_data = {
            'srs': 3857,
            'geom': polygon.ExportToWkt(),
            'layers': layers,
        }

        identify_point = self._session.post(
            f'{self._host}/{self._api["identify"]}',
            json=request_data,
            headers={
                'X-Requested-With': 'XMLHttpRequest',
            }
        )

        if identify_point.status_code != 200:
            return web.json_response({
                'error': f'Server returned {identify_point.status_code} response status code',
            })

        identify_json = identify_point.json()
        feature_list = {
            'results': [],
        }
        for layer_id in identify_json:
            if not layer_id.isnumeric():
                continue

            for feature in identify_json[layer_id]['features']:
                feature['fields']['id'] = feature['id']
                feature_list['results'].append({
                    'attributes': feature['fields'],
                    'layerId': feature['layerId'],
                    'displayFieldName': 'id',
                    'value': feature['id'],
                })

        callback = request.query.get('callback', '')
        return web.Response(body=f'{callback}({json.dumps(feature_list)})')

    async def layer_info(self, request):
        callback = request.query.get('callback', '')
        return web.Response(body=f'{callback}()')
