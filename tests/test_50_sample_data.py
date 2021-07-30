import os.path
import typing as T

import py
import pytest

xr = pytest.importorskip("xarray")  # noqa

from cfgrib import xarray_store, xarray_to_grib

SAMPLE_DATA_FOLDER = os.path.join(os.path.dirname(__file__), "sample-data")


@pytest.mark.parametrize(
    "grib_name",
    [
        "era5-levels-members",
        "fields_with_missing_values",
        "lambert_grid",
        "reduced_gg",
        "regular_gg_sfc",
        "regular_gg_pl",
        "regular_gg_ml",
        "regular_gg_ml_g2",
        "regular_ll_sfc",
        "regular_ll_msl",
        "scanning_mode_64",
        "single_gridpoint",
        "spherical_harmonics",
        "t_analysis_and_fc_0",
    ],
)
def test_open_dataset(grib_name: str) -> None:
    grib_path = os.path.join(SAMPLE_DATA_FOLDER, grib_name + ".grib")
    res = xarray_store.open_dataset(grib_path, cache=False)
    print(res)


@pytest.mark.parametrize(
    "grib_name",
    [
        "hpa_and_pa",
        "t_on_different_level_types",
        "tp_on_different_grid_resolutions",
        "uv_on_different_levels",
    ],
)
def test_open_dataset_fail(grib_name: str) -> None:
    grib_path = os.path.join(SAMPLE_DATA_FOLDER, grib_name + ".grib")

    with pytest.raises(ValueError):
        xarray_store.open_dataset(grib_path, cache=False, backend_kwargs={"errors": "raise"})


@pytest.mark.parametrize(
    "grib_name", ["hpa_and_pa", "t_on_different_level_types", "tp_on_different_grid_resolutions"]
)
def test_open_datasets(grib_name: str) -> None:
    grib_path = os.path.join(SAMPLE_DATA_FOLDER, grib_name + ".grib")

    res = xarray_store.open_datasets(grib_path)

    assert len(res) > 1


@pytest.mark.parametrize(
    "grib_name",
    [
        "era5-levels-members",
        "fields_with_missing_values",
        pytest.param("lambert_grid", marks=pytest.mark.xfail),
        "reduced_gg",
        "regular_gg_sfc",
        "regular_gg_pl",
        "regular_gg_ml",
        pytest.param("regular_gg_ml_g2", marks=pytest.mark.xfail),
        "regular_ll_sfc",
        "regular_ll_msl",
        "scanning_mode_64",
        pytest.param("spherical_harmonics", marks=pytest.mark.xfail),
        "t_analysis_and_fc_0",
    ],
)
def test_canonical_dataset_to_grib(grib_name: str, tmpdir: py.path.local) -> None:
    grib_path = os.path.join(SAMPLE_DATA_FOLDER, grib_name + ".grib")
    out_path = str(tmpdir.join(grib_name + ".grib"))

    res = xarray_store.open_dataset(grib_path)

    with pytest.warns(FutureWarning):
        xarray_to_grib.canonical_dataset_to_grib(res, out_path)
    reread = xarray_store.open_dataset(out_path)
    assert res.equals(reread)


@pytest.mark.parametrize(
    "grib_name,ndims", [("era5-levels-members", 1), ("era5-single-level-scalar-time", 0),],
)
def test_open_dataset_extra_coords(grib_name: str, ndims: T.Any) -> None:
    grib_path = os.path.join(SAMPLE_DATA_FOLDER, grib_name + ".grib")
    res = xarray_store.open_dataset(
        grib_path,
        backend_kwargs={"extra_coords": {"experimentVersionNumber": "time"}},
        cache=False,
    )
    assert "experimentVersionNumber" in res.coords
    assert len(res["experimentVersionNumber"].dims) == ndims
