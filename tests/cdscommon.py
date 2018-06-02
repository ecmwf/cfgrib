
import hashlib
import os
import shutil

import cdsapi

SAMPLE_DATA_FOLDER = os.path.join(os.path.dirname(__file__), 'sample-data')
EXTENSIONS = {'grib': '.grib', 'netcdf': '.nc'}


def ensure_data(dataset, request, folder=SAMPLE_DATA_FOLDER, name='{uuid}.grib'):
    request_text = str(sorted(request.items())).encode('utf-8')
    uuid = hashlib.sha3_224(request_text).hexdigest()[:10]
    format = request.get('format', 'grib')
    ext = EXTENSIONS.get(format, '.bin')
    name = name.format(**locals())
    path = os.path.join(SAMPLE_DATA_FOLDER, name)
    if not os.path.exists(path):
        c = cdsapi.Client()
        try:
            c.retrieve(dataset, request, target=path + '.tmp')
            shutil.move(path + '.tmp', path)
        except:
            os.unlink(path + '.tmp')
            raise
    return path
