
from __future__ import absolute_import, division, print_function, unicode_literals

from cf2cdm import cfunits


def test_are_convertible():
    assert cfunits.are_convertible('hPa', 'Pa')
    assert not cfunits.are_convertible('m', 'Pa')
