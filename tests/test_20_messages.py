
from __future__ import absolute_import, division, print_function, unicode_literals

import os.path

from eccodes_grib import eccodes
from eccodes_grib import messages


TEST_DATA = os.path.join(os.path.dirname(__file__), 'sample-data', 'ERA5_levels.grib')


def test_Message():
    codes_id = eccodes.grib_new_from_file(open(TEST_DATA))
    res = messages.Message(codes_id=codes_id)

    assert res['paramId'] == 130
    assert list(res)[0] == 'globalDomain'
    assert 'paramId' in res
    assert len(res) == 192

    list(res.items())


def test_Stream():
    res = messages.Stream(TEST_DATA)
    assert len(res.first()) == 192
    assert sum(1 for _ in res) == 72
