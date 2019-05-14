import pytest

xr = pytest.importorskip('xarray')  # noqa

from cf2cdm import cfunits


def test_are_convertible():
    assert cfunits.are_convertible('K', 'K')
    assert cfunits.are_convertible('m', 'meters')
    assert cfunits.are_convertible('hPa', 'Pa')
    assert not cfunits.are_convertible('m', 'Pa')
