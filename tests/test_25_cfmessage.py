
from __future__ import absolute_import, division, print_function, unicode_literals

import os.path

from cfgrib import cfmessage

SAMPLE_DATA_FOLDER = os.path.join(os.path.dirname(__file__), 'sample-data')
TEST_DATA = os.path.join(SAMPLE_DATA_FOLDER, 'era5-levels-members.grib')


def test_from_grib_date_time():
    message = {
        'dataDate': 20160706,
        'dataTime': 1944,
    }
    result = cfmessage.from_grib_date_time(message)

    assert result == 1467834240
