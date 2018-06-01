
import pytest

import eccodes_grib

import cdscommon


REQUESTS = {
    'seasonal-original-single-levels': ({
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
        'grid': [3, 3],
        'format': 'grib',
    }, 192),
    'seasonal-original-pressure-levels': ({
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
        'grid': [3, 3],
        'format': 'grib',
    }, 192),
    'seasonal-postprocessed-single-levels': ({
        'originating_centre': 'ukmo',
        'variable': 'maximum_2m_temperature_in_the_last_24_hours_anomaly',
        'product_type': 'monthly_mean',
        'year': '2018',
        'month': ['04', '05'],
        'leadtime_month': ['1', '2'],
        'grid': [3, 3],
        'format': 'grib',
    }, 210),
    'seasonal-monthly-single-levels': ({
        'originating_centre': 'ukmo',
        'variable': 'maximum_2m_temperature_in_the_last_24_hours',
        'product_type': 'monthly_mean',
        'year': '2018',
        'month': ['04', '05'],
        'leadtime_month': ['1', '2'],
        'grid': [3, 3],
        'format': 'grib'
    }, 210),
}
EUROPE_EXTENT = {'latitude': slice(65, 30), 'longitude': slice(0, 40)}


@pytest.mark.parametrize('dataset', REQUESTS.keys())
def test_Stream(dataset):
    request, key_count = REQUESTS[dataset]
    path = cdscommon.ensure_data(dataset, request)

    stream = eccodes_grib.Stream(path)
    leader = stream.first()
    assert len(leader) == key_count
    assert sum(1 for _ in stream) == leader['count']


@pytest.mark.parametrize('dataset', REQUESTS.keys())
def test_Dataset(dataset):
    request, _ = REQUESTS[dataset]
    path = cdscommon.ensure_data(dataset, request)

    eccodes_grib.Dataset(path)
