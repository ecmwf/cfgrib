
import os.path

import pytest
xr = pytest.importorskip('xarray')  # noqa

from cf2cdm import cfcoords
from cf2cdm import datamodels
from cfgrib import xarray_store

SAMPLE_DATA_FOLDER = os.path.join(os.path.dirname(__file__), 'sample-data')
TEST_DATA = os.path.join(SAMPLE_DATA_FOLDER, 'era5-levels-members.grib')


def test_cds():
    ds = xarray_store.open_dataset(TEST_DATA)

    res = cfcoords.translate_coords(ds, coord_model=datamodels.CDS)

    assert set(res.dims) == {'forecast_reference_time', 'lat', 'lon', 'plev', 'realization'}


def test_ecmwf():
    ds = xarray_store.open_dataset(TEST_DATA)

    res = cfcoords.translate_coords(ds, coord_model=datamodels.ECMWF)

    assert set(res.dims) == {'time', 'latitude', 'longitude', 'level', 'number'}
