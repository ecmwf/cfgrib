
import pytest

import cfgrib
import cfgrib.xarray_store

import cdscommon


TEST_FILES = {
    'era5-single-levels-reanalysis': [
        'reanalysis-era5-single-levels',
        {
            'variable': '2m_temperature',
            'product_type': 'reanalysis',
            'year': '2017',
            'month': '01',
            'day': ['01', '02'],
            'time': ['00:00', '12:00'],
            'grid': ['3', '3'],
            'format': 'grib',
        },
        191,
    ],
    'era5-single-levels-ensemble_members': [
        'reanalysis-era5-single-levels',
        {
            'variable': '2m_temperature',
            'product_type': 'ensemble_members',
            'year': '2017',
            'month': '01',
            'day': ['01', '02'],
            'time': ['00:00', '12:00'],
            'grid': ['3', '3'],
            'format': 'grib',
        },
        192,
    ],
    'era5-pressure-levels-reanalysis': [
        'reanalysis-era5-pressure-levels',
        {
            'variable': 'temperature',
            'pressure_level': ['500', '850'],
            'product_type': 'reanalysis',
            'year': '2017',
            'month': '01',
            'day': ['01', '02'],
            'time': ['00:00', '12:00'],
            'grid': ['3', '3'],
            'format': 'grib',
        },
        191,
    ],
    'era5-pressure-levels-ensemble_members': [
        'reanalysis-era5-pressure-levels',
        {
            'variable': 'temperature',
            'pressure_level': ['500', '850'],
            'product_type': 'ensemble_members',
            'year': '2017',
            'month': '01',
            'day': ['01', '02'],
            'time': ['00:00', '12:00'],
            'grid': ['3', '3'],
            'format': 'grib',
        },
        192,
    ],
    'era5-single-levels-reanalysis-area': [
        'reanalysis-era5-single-levels',
        {
            'variable': '2m_temperature',
            'product_type': 'reanalysis',
            'year': '2017',
            'month': '01',
            'day': ['01', '02'],
            'time': ['00:00', '12:00'],
            'area': ['35.5', '6.5', '47.', '19.'],
            'format': 'grib',
        },
        191,
    ],
}


@pytest.mark.parametrize('test_file', TEST_FILES.keys())
def test_Stream(test_file):
    dataset, request, key_count = TEST_FILES[test_file]
    path = cdscommon.ensure_data(dataset, request, name='cds-' + test_file + '-{uuid}.grib')

    stream = cfgrib.FileStream(path)
    leader = stream.first()
    assert len(leader) == key_count
    assert sum(1 for _ in stream) == leader['count']


@pytest.mark.parametrize('test_file', TEST_FILES.keys())
def test_Dataset(test_file):
    dataset, request, key_count = TEST_FILES[test_file]
    path = cdscommon.ensure_data(dataset, request, name='cds-' + test_file + '-{uuid}.grib')

    res = cfgrib.xarray_store.open_dataset(path, flavour_name='cds')
    res.to_netcdf(path[:-5] + '.nc')


@pytest.mark.skip()
def test_large_Dataset():
    dataset, request, key_count = TEST_FILES['era5-pressure-levels-ensemble_members']
    # make the request large
    request['day'] = list(range(1, 32))
    request['time'] = list(['%02d:00' % h for h in range(0, 24, 3)])
    path = cdscommon.ensure_data(dataset, request, name='cds-' + dataset + '-LARGE-{uuid}.grib')

    res = cfgrib.xarray_store.open_dataset(path, flavour_name='cds')
    res.to_netcdf(path[:-5] + '.nc')
