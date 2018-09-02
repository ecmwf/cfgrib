
import pytest

import cfgrib

import cdscommon


TEST_FILES = {
    'seasonal-original-single-levels-ukmo': [
        'seasonal-original-single-levels',
        {
            'originating_centre': 'ukmo',
            'variable': 'maximum_2m_temperature_in_the_last_24_hours',
            'year': '2018',
            'month': ['04', '05'],
            'day': [
                '01', '02', '03', '04', '05', '06', '07', '08', '09', '10', '11', '12',
                '13', '14', '15', '16', '17', '18', '19', '20', '21', '22', '23', '24',
                '25', '26', '27', '28', '29', '30', '31'
            ],
            'leadtime_hour': ['24', '48'],
            'grid': ['3', '3'],
            'format': 'grib',
        },
        192,
    ],
    'seasonal-original-pressure-levels-ukmo': [
        'seasonal-original-pressure-levels',
        {
            'originating_centre': 'ukmo',
            'variable': 'temperature',
            'pressure_level': ['500', '850'],
            'year': '2018',
            'month': ['04', '05'],
            'day': [
                '01', '02', '03', '04', '05', '06', '07', '08', '09', '10', '11', '12',
                '13', '14', '15', '16', '17', '18', '19', '20', '21', '22', '23', '24',
                '25', '26', '27', '28', '29', '30', '31'
            ],
            'leadtime_hour': ['24', '48'],
            'grid': ['3', '3'],
            'format': 'grib',
        },
        192,
    ],
    'seasonal-postprocessed-single-levels-ukmo': [
        'seasonal-postprocessed-single-levels',
        {
            'originating_centre': 'ukmo',
            'variable': 'maximum_2m_temperature_in_the_last_24_hours_anomaly',
            'product_type': 'monthly_mean',
            'year': '2018',
            'month': ['04', '05'],
            'leadtime_month': ['1', '2'],
            'grid': ['3', '3'],
            'format': 'grib',
        },
        210,
    ],
    'seasonal-monthly-single-levels-monthly_mean-ukmo': [
        'seasonal-monthly-single-levels',
        {
            'originating_centre': 'ukmo',
            'variable': 'maximum_2m_temperature_in_the_last_24_hours',
            'product_type': 'monthly_mean',
            'year': '2018',
            'month': ['04', '05'],
            'leadtime_month': ['1', '2'],
            'grid': ['3', '3'],
            'format': 'grib',
        },
        210,
    ],
    'seasonal-monthly-single-levels-ensemble_mean-ukmo': [
        'seasonal-monthly-single-levels',
        {
            'originating_centre': 'ukmo',
            'variable': 'maximum_2m_temperature_in_the_last_24_hours',
            'product_type': 'ensemble_mean',
            'year': '2018',
            'month': ['04', '05'],
            'leadtime_month': ['1', '2'],
            'grid': ['3', '3'],
            'format': 'grib',
        },
        210,
    ],
    'seasonal-monthly-single-levels-hindcast_climate_mean-ukmo': [
        'seasonal-monthly-single-levels',
        {
            'originating_centre': 'ukmo',
            'variable': 'maximum_2m_temperature_in_the_last_24_hours',
            'product_type': 'hindcast_climate_mean',
            'year': '2018',
            'month': ['04', '05'],
            'leadtime_month': ['1', '2'],
            'grid': ['3', '3'],
            'format': 'grib',
        },
        210,
    ],
}


@pytest.mark.parametrize('test_file', TEST_FILES.keys())
def test_reanalysis_Stream(test_file):
    dataset, request, key_count = TEST_FILES[test_file]
    path = cdscommon.ensure_data(dataset, request, name='cds-' + test_file + '-{uuid}.grib')

    stream = cfgrib.FileStream(path)
    leader = stream.first()
    assert len(leader) == key_count
    assert sum(1 for _ in stream) == leader['count']


@pytest.mark.parametrize('test_file', TEST_FILES.keys())
def test_reanalysis_Dataset(test_file):
    dataset, request, key_count = TEST_FILES[test_file]
    path = cdscommon.ensure_data(dataset, request, name='cds-' + test_file + '-{uuid}.grib')

    res = cfgrib.xarray_store.open_dataset(path, flavour_name='cds')
    res.to_netcdf(path[:-5] + '.nc')
