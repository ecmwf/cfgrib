
import pytest

import eccodes_grib

import cdscommon


REQUESTS = {
    'reanalysis-era5-single-levels': {
        'variable': '2m_temperature',
        'product_type': 'reanalysis',
        'year': '2017',
        'month': '01',
        'day': '01',
        'time': ['00:00', '12:00'],
        'grid': [3, 3],
        'format': 'grib',
    },
    'reanalysis-era5-pressure-levels': {
        'variable': 'temperature',
        'pressure_level': ['500', '850'],
        'product_type': 'ensemble_members',
        'year': '2017',
        'month': '01',
        'day': '01',
        'time': ['00:00', '12:00'],
        'grid': [3, 3],
        'format': 'grib',
    },
}
EUROPE_EXTENT = {'latitude': slice(65, 30), 'longitude': slice(0, 40)}


@pytest.mark.parametrize('dataset', REQUESTS.keys())
def test_reanalysis_Stream(dataset):
    request = REQUESTS[dataset]
    path = cdscommon.ensure_data(dataset, request)

    stream = eccodes_grib.Stream(path)
    leader = stream.first()
    assert len(leader) in (191, 192)
    assert sum(1 for _ in stream) == leader['count']


@pytest.mark.parametrize('dataset', REQUESTS.keys())
def test_reanalysis_Dataset(dataset):
    request = REQUESTS[dataset]
    path = cdscommon.ensure_data(dataset, request)

    res = eccodes_grib.Dataset(path)
    assert len(res.variables) == 1
