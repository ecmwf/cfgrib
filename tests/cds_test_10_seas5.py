
import pytest

import eccodes_grib

import cdscommon


REQUESTS = {
    'seasonal-original-single-levels': {
        'originating_centre': 'ecmwf',
        'variable': 'maximum_2m_temperature_in_the_last_24_hours',
        'year': '2018',
        'month': ['04', '05'],
        'day': '01',
        'leadtime_hour': ['24', '48'],
        'grid': [3, 3],
        'format': 'grib',
    },
    'seasonal-postprocessed-single-levels': {
        'originating_centre': 'ecmwf',
        'variable': 'maximum_2m_temperature_in_the_last_24_hours_anomaly',
        'product_type': 'monthly_mean',
        'year': '2018',
        'month': ['04', '05'],
        'leadtime_month': ['1', '2'],
        'grid': [3, 3],
        'format': 'grib',
    },
    'seasonal-monthly-single-levels': {
        'originating_centre': 'ecmwf',
        'variable': 'maximum_2m_temperature_in_the_last_24_hours',
        'product_type': 'monthly_mean',
        'year': '2018',
        'month': ['04', '05'],
        'leadtime_month': ['1', '2'],
        'grid': [3, 3],
        'format': 'grib'
    },
}
EUROPE_EXTENT = {'latitude': slice(65, 30), 'longitude': slice(0, 40)}


@pytest.mark.parametrize('dataset', REQUESTS.keys())
def test_ecmwf_monthly_mean_Stream(dataset):
    request = REQUESTS[dataset]
    path = cdscommon.ensure_data(dataset, request)

    stream = eccodes_grib.Stream(path)
    leader = stream.first()
    assert len(leader) > 10
    assert sum(1 for _ in stream) == cdscommon.message_count(dataset, request)


@pytest.mark.parametrize('dataset', REQUESTS.keys())
def test_ecmwf_monthly_mean_Dataset(dataset):
    path = cdscommon.ensure_data(dataset, REQUESTS[dataset])

    eccodes_grib.Dataset(path)
