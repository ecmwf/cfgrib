
import pytest

import eccodes_grib

import cdscommon


TEST_FIƒ131LES = {
    'era5-levels-members-one_var': [
        'reanalysis-era5-pressure-levels',
        {
            'variable': 'temperature',
            'pressure_level': ['500', '850'],
            'product_type': 'ensemble_members',
            'year': '2017',
            'month': '01',
            'day': '01',
            'time': ['00:00', '12:00'],
            'grid': ['3', '3'],
            'format': 'grib'
        },
        192,
    ],
    'era5-levels-members-many_vars': [
        'reanalysis-era5-pressure-levels',
        {
            'variable': ['geopotential', 'temperature'],
            'pressure_level': ['500', '850'],
            'product_type': 'ensemble_members',
            'year': '2017',
            'month': '01',
            'day': '01',
            'time': ['00:00', '12:00'],
            'grid': ['3', '3'],
            'format': 'grib'
        },
        192,
    ],
}


@pytest.mark.parametrize('test_file', TEST_FILES.keys())
def test_reanalysis_Stream(test_file):
    dataset, request, key_count = TEST_FILES[test_file]
    path = cdscommon.ensure_data(dataset, request, name=test_file + '.grib')

    stream = eccodes_grib.Stream(path)
    leader = stream.first()
    assert len(leader) == key_count
    assert sum(1 for _ in stream) == leader['count']
