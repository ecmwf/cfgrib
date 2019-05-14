import pytest

import cfgrib

import cdscommon


TEST_FILES = {
    'era5-levels-members': [
        'reanalysis-era5-pressure-levels',
        {
            'variable': ['geopotential', 'temperature'],
            'pressure_level': ['500', '850'],
            'product_type': 'ensemble_members',
            'year': '2017',
            'month': '01',
            'day': ['01', '02'],
            'time': ['00:00', '12:00'],
            'grid': ['3', '3'],
            'format': 'grib',
        },
        193,
    ]
}


@pytest.mark.parametrize('test_file', TEST_FILES.keys())
def test_reanalysis_Stream(test_file):
    dataset, request, key_count = TEST_FILES[test_file]
    path = cdscommon.ensure_data(dataset, request, name=test_file + '{ext}')

    stream = cfgrib.FileStream(path)
    leader = stream.first()
    assert len(leader) == key_count
    assert sum(1 for _ in stream) == leader['count']
