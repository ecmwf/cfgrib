
import hashlib
import os
import shutil

import cdsapi

import eccodes_grib


SAMPLE_DATA_FOLDER = os.path.join(os.path.dirname(__file__), 'sample-data')

DATASET = 'seasonal-postprocessed-single-levels'
REQUEST = {
    'originating_centre': 'ecmwf',
    'variable': [
        'maximum_2m_temperature_in_the_last_24_hours_anomaly',
        'minimum_2m_temperature_in_the_last_24_hours_anomaly'
    ],
    'product_type': 'monthly_mean',
    'year': '2018',
    'month': ['04', '05'],
    'leadtime_month': ['1', '2', '3', '4', '5', '6'],
    'grid': [3, 3],
    'format': 'grib'
}
EUROPE_EXTENT = {'latitude': slice(65, 30), 'longitude': slice(0, 40)}


def ensure_data(dataset, request, folder=SAMPLE_DATA_FOLDER):
    request_text = str(sorted(request.items())).encode('utf-8')
    uuid = hashlib.sha3_224(request_text).hexdigest()[:10]
    name = 'cds-{dataset}-{uuid}.grib'.format(**locals())
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


def test_ecmwf_monthly_mean_Stream():
    path = ensure_data(DATASET, REQUEST)

    stream = eccodes_grib.Stream(path)
    leader = stream.first()
    assert len(leader) == 210
    assert sum(1 for _ in stream) == 1224


def test_ecmwf_monthly_mean_Dataset():
    path = ensure_data(DATASET, REQUEST)

    eccodes_grib.Dataset(path)
