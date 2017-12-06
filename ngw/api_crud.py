import json
from aiohttp import web
from osgeo import ogr, osr

from ngw.common import NGW, NGWException

# TRANSFORM_URL = 'http://tasks.arcgisonline.com/arcgis/rest/services/Geometry/GeometryServer/project'


class CrudHandler(NGW):
    def __init__(self, host, username, password):
        super().__init__(host, username, password)

        # self._layer_map = {
        #     'default': 33,
        #     'arrow': 14,
        #     'point': 33,
        # }
        # self._styles_layer_map = {
        #     'point': 'point',
        #     'big_point': 'point',
        #     'green_point': 'point',
        #     'arrow': 'arrow',
        # }
        self._geojson_type_map = {
            'POINT': 'Point',
            'MULTIPOINT': 'MultiPoint',
            'MULTILINESTRING': 'MultiLineString',
            'POLYGON': 'Polygon',
        }

    async def save(self, request):
        if not self._is_auth:
            try:
                self._ngw_auth()

            except NGWException as ex:
                return web.json_response({
                    'error': ex,
                })

        request_data = await request.json()
        if not isinstance(request_data, dict) or 'layer' not in request_data \
                or ('id' not in request_data and 'geometry' not in request_data):
            return web.json_response({
                'error': 'Invalid request body',
                'description': 'Expected dict',
            }, status=400)

        prepare = {
            'extensions': {
                'attachment': None,
                'description': None,
            },
            'fields': {
                # 'style': request_data.get('style', 'default'),
            }
        }

        if request_data.get('caption') is not None:
            prepare['fields']['caption'] = request_data.pop('caption')

        try:
            layer = request_data.pop('layer')
            info = self._ngw_info(layer)

        except NGWException as ex:
            return web.json_response({
                'error': ex,
            }, status=400)

        if request_data.get('geometry') is not None:
            prepare['geom'] = request_data.pop('geometry')
            if not isinstance(prepare['geom'], str):
                try:
                    geojson = {
                        'type': self._geojson_type_map[info['postgis_layer']['geometry_type'].upper()],
                        'coordinates': prepare['geom'],
                    }
                    prepare['geom'] = self.transform_epsg(json.dumps(geojson), 4326, 3857, out_format='wkt')

                except Exception as ex:
                    return web.json_response({
                        'error': f'Invalid geometry field. Exception: {str(ex)}',
                        'description': 'Please read http://gis-lab.info/docs/geojson_ru.html#2.1.5',
                    }, status=400)

        # if isinstance(request_data.get('group_list'), (list, tuple,)):
        #     post['fields']['group_list'] = ','.join(map(str, request_data['group_list']))
        #
        # else:
        #     post['fields']['group_list'] = request_data['group_list']

        if request_data.get('id') is not None:
            feature_id = request_data.pop('id')
            url = self._api['edit'].format(layer_p=layer, feature_p=feature_id)
            kwargs = {
                'method': 'PUT',
                'url': f'{self._host}/{url}',
            }
            # prepare['id'] = feature_id

        else:
            url = self._api['create'].format(layer_p=layer)
            kwargs = {
                'method': 'POST',
                'url': f'{self._host}/{url}',
            }

        # Others attributes
        prepare['fields'].update(request_data)

        save_response = self._session.request(**kwargs, json=prepare)
        return web.json_response({
            'successfully': save_response.status_code == 200,
            'response': save_response.json(),
        })

    @staticmethod
    def geojson_to_esri(coordinates, geometry=None):
        if geometry is None:
            geometry = {
                'geometryType': 'esriGeometryPoint',
                'geometries': [],
            }

        if len(coordinates) > 0 and isinstance(coordinates[0], (list, tuple,)):
            for child in coordinates:
                geometry = CrudHandler.geojson_to_esri(child, geometry)

        else:
            geometry['geometries'].append(dict(zip(('x', 'y', 'z'), coordinates)))

        return geometry

    @staticmethod
    def esri_to_geojson(point_list, coordinates):
        if len(coordinates) > 0 and isinstance(coordinates[0], (list, tuple,)):
            for child in coordinates:
                CrudHandler.esri_to_geojson(point_list, child)

        else:
            point = point_list.pop()
            coordinates.clear()
            for dimension in ('x', 'y', 'z'):
                if dimension in point:
                    coordinates.append(point[dimension])

        return coordinates

    @staticmethod
    def transform_epsg(geojson, in_epsg, out_epsg, out_format='GeoJSON'):
        # create a geometry from coordinates
        geometry = ogr.CreateGeometryFromJson(geojson)

        # create coordinate transformation
        in_srs = osr.SpatialReference()
        in_srs.ImportFromEPSG(in_epsg)
        out_srs = osr.SpatialReference()
        out_srs.ImportFromEPSG(out_epsg)

        coord_transform = osr.CoordinateTransformation(in_srs, out_srs)
        geometry.Transform(coord_transform)

        if out_format.lower() == 'geojson':
            return geometry.ExportToJson()
        elif out_format.lower() == 'wkt':
            return geometry.ExportToIsoWkt()
