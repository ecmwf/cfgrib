
from __future__ import absolute_import, division, print_function, unicode_literals

import os.path
import numpy as np

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


def test_to_grib_date_time():
    message = {}
    datetime_ns = int(np.datetime64('2001-10-11T01:01:00', 'ns'))

    cfmessage.to_grib_date_time(message, datetime_ns)

    assert message['dataDate'] == 20011011
    assert message['dataTime'] == 101


def test_from_grib_step():
    message = {
        'endStep': 1,
        'stepUnits': 1,
    }
    step_seconds = cfmessage.from_grib_step(message)

    assert step_seconds == 1


def test_to_grib_step():
    message = {}
    step_ns = 60 * 60 * 1e9

    cfmessage.to_grib_step(message, step_ns, step_unit=1)

    assert message['endStep'] == 1
    assert message['stepUnits'] == 1
