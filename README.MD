Middleware for NextGIS Web

If you wish use ArcGIS JavaScript API for displaying your NextGIS web map that script is your friend.

For displaying you just need add new ArcGISDynamicMapServiceLayer to map by url like a this:
"http://middleware_host:8000/<NextGis_Webmap_ID>/MapServer"

You can set visible layers IDs, or script himself will get all layers from NextGIS Web

Supported features:
- Adding new objects to map and editing old objects
- Receiving map info
- Receiving map layers
- Identifying objects by click

ToDo:
- Displaying legend


Installation:
IMPORTANT! Script needs Python3.6 and above!

For start web server you need install all dependencies.
Just execute "pip install -r ./requirements.txt" in your virtual env or global

If you will use gunicorn, you need install it separately!

Edit the config file (etc/config.py) to according your values

Run web server:
Gunicorn command: "bin/gunicorn main:app --bind 0.0.0.0:8000 --workers 3 --worker-class aiohttp.worker.GunicornWebWorker"
Run for testing and development: "python ./main.py"
