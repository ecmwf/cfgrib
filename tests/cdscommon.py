
import hashlib
import os
import shutil

import cdsapi

SAMPLE_DATA_FOLDER = os.path.join(os.path.dirname(__file__), 'sample-data')


def ensure_data(dataset, request, folder=SAMPLE_DATA_FOLDER, name='{uuid}.grib'):
    request_text = str(sorted(request.items())).encode('utf-8')
    uuid = hashlib.sha3_224(request_text).hexdigest()[:10]
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


def message_count(dataset, request, count=1):
    if dataset == 'reanalysis-era5-single-levels' \
            and request.get('product_type') == 'ensemble_members':
        count = 20
    elif dataset == 'reanalysis-era5-pressure-levels' \
            and request.get('product_type') == 'ensemble_members':
        count = 20
    elif dataset == 'seasonal-original-single-levels':
        count = 51
    elif dataset.startswith('seasonal-') and request.get('product_type') == 'monthly_mean':
        count = 51
    for key in ['year', 'month', 'day', 'time', 'leadtime_hour', 'leadtime_month']:
        value = request.get(key)
        if isinstance(value, list):
            count *= len(value)
    return count
