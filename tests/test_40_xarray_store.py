import os.path

import gribapi  # type: ignore
import numpy as np
import pandas as pd
import pytest

xr = pytest.importorskip("xarray")  # noqa

from cfgrib import dataset, xarray_store

SAMPLE_DATA_FOLDER = os.path.join(os.path.dirname(__file__), "sample-data")
TEST_DATA = os.path.join(SAMPLE_DATA_FOLDER, "era5-levels-members.grib")
TEST_CORRUPTED = os.path.join(SAMPLE_DATA_FOLDER, "era5-levels-corrupted.grib")
TEST_DATASETS = os.path.join(SAMPLE_DATA_FOLDER, "t_on_different_level_types.grib")
TEST_IGNORE = os.path.join(SAMPLE_DATA_FOLDER, "uv_on_different_levels.grib")
TEST_DATA_NCEP_MONTHLY = os.path.join(SAMPLE_DATA_FOLDER, "ncep-seasonal-monthly.grib")
TEST_DATA_MULTIPLE_FIELDS = os.path.join(SAMPLE_DATA_FOLDER, "regular_gg_ml_g2.grib")
TEST_DATA_DIFFERENT_STEP_TYPES = os.path.join(SAMPLE_DATA_FOLDER, "cfrzr_and_cprat.grib")
TEST_DATA_DIFFERENT_STEP_TYPES_ZEROS = os.path.join(SAMPLE_DATA_FOLDER, "cfrzr_and_cprat_0s.grib")
TEST_DATA_STEPS_IN_MINUTES = os.path.join(SAMPLE_DATA_FOLDER, "step_60m.grib")
TEST_DATA_ALTERNATE_ROWS_MERCATOR = os.path.join(SAMPLE_DATA_FOLDER, "ds.waveh.5.grib")


def test_open_dataset() -> None:
    res = xarray_store.open_dataset(TEST_DATA)

    assert res.attrs["GRIB_edition"] == 1

    var = res["t"]
    assert var.attrs["GRIB_gridType"] == "regular_ll"
    assert var.attrs["units"] == "K"
    assert var.dims == ("number", "time", "isobaricInhPa", "latitude", "longitude")

    assert var.mean() > 0.0

    with pytest.raises(ValueError):
        xarray_store.open_dataset(TEST_DATA, engine="any-other-engine")

    res = xarray_store.open_dataset(TEST_IGNORE, backend_kwargs={"errors": "warn"})
    assert "isobaricInhPa" in res.dims

    res = xarray_store.open_dataset(TEST_IGNORE, backend_kwargs={"errors": "ignore"})
    assert "isobaricInhPa" in res.dims

    with pytest.raises(dataset.DatasetBuildError):
        xarray_store.open_dataset(TEST_IGNORE, backend_kwargs={"errors": "raise"})

    xarray_store.open_dataset(TEST_DATA, backend_kwargs={"errors": "raise"})


def test_open_dataset_corrupted() -> None:
    res = xarray_store.open_dataset(TEST_CORRUPTED)

    assert res.attrs["GRIB_edition"] == 1
    assert len(res.data_vars) == 1

    with pytest.raises(gribapi.GribInternalError):
        xarray_store.open_dataset(TEST_CORRUPTED, backend_kwargs={"errors": "raise"})


def test_open_dataset_encode_cf_time() -> None:
    backend_kwargs = {"encode_cf": ("time",)}
    res = xarray_store.open_dataset(TEST_DATA, backend_kwargs=backend_kwargs)

    assert res.attrs["GRIB_edition"] == 1
    assert res["t"].attrs["GRIB_gridType"] == "regular_ll"
    assert res["t"].attrs["GRIB_units"] == "K"
    assert res["t"].dims == ("number", "time", "level", "values")

    assert res["t"].mean() > 0.0


def test_open_dataset_encode_cf_vertical() -> None:
    backend_kwargs = {"encode_cf": ("vertical",)}
    res = xarray_store.open_dataset(TEST_DATA, backend_kwargs=backend_kwargs)

    var = res["t"]
    assert var.dims == ("number", "dataDate", "dataTime", "isobaricInhPa", "values")

    assert var.mean() > 0.0


def test_open_dataset_encode_cf_geography() -> None:
    backend_kwargs = {"encode_cf": ("geography",)}
    res = xarray_store.open_dataset(TEST_DATA, backend_kwargs=backend_kwargs)

    assert res.attrs["GRIB_edition"] == 1

    var = res["t"]
    assert var.attrs["GRIB_gridType"] == "regular_ll"
    assert var.attrs["GRIB_units"] == "K"
    assert var.dims == ("number", "dataDate", "dataTime", "level", "latitude", "longitude")

    assert var.mean() > 0.0


def test_open_dataset_extra_coords_attrs() -> None:
    backend_kwargs = {
        "time_dims": ("forecastMonth", "indexing_time"),
        "extra_coords": {"time": "number"},
    }

    res = xarray_store.open_dataset(TEST_DATA_NCEP_MONTHLY, backend_kwargs=backend_kwargs)
    assert "time" in res.variables
    assert res.variables["time"].dims == ("number",)
    assert res.variables["time"].data[0] == np.datetime64("2021-09-01T00:00:00")
    assert res.variables["time"].data[123] == np.datetime64("2021-08-02T00:18:00")
    assert res.variables["time"].attrs["standard_name"] == "forecast_reference_time"


def test_open_dataset_eccodes() -> None:
    res = xarray_store.open_dataset(TEST_DATA)

    assert res.attrs["GRIB_edition"] == 1

    var = res["t"]
    assert var.attrs["GRIB_gridType"] == "regular_ll"
    assert var.attrs["units"] == "K"
    assert var.dims == ("number", "time", "isobaricInhPa", "latitude", "longitude")

    assert var.mean() > 0.0


def test_open_datasets() -> None:
    res = xarray_store.open_datasets(TEST_DATASETS)

    assert len(res) > 1
    assert res[0].attrs["GRIB_centre"] == "ecmf"


def test_cached_geo_coords() -> None:
    ds1 = xarray_store.open_dataset(TEST_DATA_MULTIPLE_FIELDS)
    ds2 = xarray_store.open_dataset(
        TEST_DATA_MULTIPLE_FIELDS, backend_kwargs=dict(cache_geo_coords=False)
    )
    assert ds2.identical(ds1)


def test_open_datasets_differet_step_types() -> None:
    res = xarray_store.open_datasets(TEST_DATA_DIFFERENT_STEP_TYPES)

    assert len(res) == 2
    assert res[0].cprat.attrs["GRIB_stepType"] == "instant"
    assert res[0].cfrzr.attrs["GRIB_stepType"] == "instant"
    assert res[1].cprat.attrs["GRIB_stepType"] == "avg"
    assert res[1].cfrzr.attrs["GRIB_stepType"] == "avg"


# test the case where we have two different step types, but the data values
# are all zero - we should still separate into differernt datasets
def test_open_datasets_differet_step_types_zeros() -> None:
    res = xarray_store.open_datasets(TEST_DATA_DIFFERENT_STEP_TYPES_ZEROS)

    assert len(res) == 2
    assert res[0].cprat.attrs["GRIB_stepType"] == "instant"
    assert res[0].cfrzr.attrs["GRIB_stepType"] == "instant"
    assert res[1].cprat.attrs["GRIB_stepType"] == "avg"
    assert res[1].cfrzr.attrs["GRIB_stepType"] == "avg"


# ensure that the encoding of the coordinates is preserved
def test_open_datasets_differet_preserve_coordinate_encoding() -> None:
    res = xarray_store.open_datasets(TEST_DATA_DIFFERENT_STEP_TYPES)
    assert len(res) == 2
    assert "units" in res[0].valid_time.encoding
    assert "units" in res[1].valid_time.encoding

    res = xarray_store.open_datasets(TEST_DATA_DIFFERENT_STEP_TYPES_ZEROS)
    assert len(res) == 2
    assert "units" in res[0].valid_time.encoding
    assert "units" in res[1].valid_time.encoding


def test_open_dataset_steps_in_minutes() -> None:
    res = xarray_store.open_dataset(TEST_DATA_STEPS_IN_MINUTES)

    var = res["t2m"]
    steps = var.step
    assert steps[0] == pd.Timedelta("0 hours")
    assert steps[1] == pd.Timedelta("1 hours")
    assert steps[5] == pd.Timedelta("5 hours")


def test_alternating_scanning_mercator() -> None:
    ds = xarray_store.open_dataset(TEST_DATA_ALTERNATE_ROWS_MERCATOR)
    values = ds.variables["shww"].data
    assert np.isnan(values[5])
    assert values[760500] == 1.5
    values_all = ds.variables["shww"].data[:]
