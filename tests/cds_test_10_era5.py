
import eccodes_grib

import cdscommon


DATASET = 'reanalysis-era5-single-levels'
REQUEST = {
    'variable': '2m_temperature',
    'product_type': 'reanalysis',
    'year': '2017',
    'month': '01',
    'day': ['01', '02', '03', '04', '05', '06', '07'],
    'time': [
        '00:00', '01:00', '02:00', '03:00', '04:00', '05:00', '06:00', '07:00', '08:00',
        '09:00', '10:00', '11:00', '12:00', '13:00', '14:00', '15:00', '16:00', '17:00',
        '18:00', '19:00', '20:00', '21:00', '22:00', '23:00'
    ],
    'grid': [3, 3],
    'format': 'grib'
}
EUROPE_EXTENT = {'latitude': slice(65, 30), 'longitude': slice(0, 40)}


def test_reanalysis_Stream():
    path = cdscommon.ensure_data(DATASET, REQUEST)

    stream = eccodes_grib.Stream(path)
    leader = stream.first()
    assert len(leader) == 191
    assert sum(1 for _ in stream) == cdscommon.message_count(REQUEST)


def test_reanalysis_Dataset():
    path = cdscommon.ensure_data(DATASET, REQUEST)

    res = eccodes_grib.Dataset(path)
    assert len(res.variables) == 1
