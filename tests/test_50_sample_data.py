
import os.path

import pytest

from cfgrib import xarray_store
from cfgrib import xarray_to_grib

SAMPLE_DATA_FOLDER = os.path.join(os.path.dirname(__file__), 'sample-data')


@pytest.mark.parametrize('grib_name', [
    'era5-levels-members',
    pytest.param('hpa_and_pa', marks=pytest.mark.xfail),
    'fields_with_missing_values',
    'lambert_grid',
    'reduced_gg',
    'regular_gg_sfc',
    'regular_gg_pl',
    'regular_gg_ml',
    'regular_gg_ml_g2',
    'regular_ll_sfc',
    'regular_ll_msl',
    'scanning_mode_64',
    'spherical_harmonics',
    't_analysis_and_fc_0',
])
def test_open_dataset(grib_name):
    grib_path = os.path.join(SAMPLE_DATA_FOLDER, grib_name + '.grib')
    res = xarray_store.open_dataset(grib_path, cache=False)
    print(res)


@pytest.mark.parametrize('grib_name', [
    't_on_different_level_types',
    'tp_on_different_grid_resolutions',
    pytest.param('uv_on_different_levels', marks=pytest.mark.xfail),
])
def test_open_dataset_fail(grib_name):
    grib_path = os.path.join(SAMPLE_DATA_FOLDER, grib_name + '.grib')
    with pytest.raises(ValueError):
        xarray_store.open_dataset(grib_path, cache=False)


# writing eccodes flavor is not supported ATM
@pytest.mark.parametrize('grib_name', [
    pytest.param('era5-levels-members', marks=pytest.mark.xfail),
    pytest.param('hpa_and_pa', marks=pytest.mark.xfail),
    pytest.param('fields_with_missing_values', marks=pytest.mark.xfail),
    pytest.param('lambert_grid', marks=pytest.mark.xfail),
    pytest.param('reduced_gg', marks=pytest.mark.xfail),
    pytest.param('regular_gg_sfc', marks=pytest.mark.xfail),
    pytest.param('regular_gg_pl', marks=pytest.mark.xfail),
    pytest.param('regular_gg_ml', marks=pytest.mark.xfail),
    pytest.param('regular_gg_ml_g2', marks=pytest.mark.xfail),
    pytest.param('regular_ll_sfc', marks=pytest.mark.xfail),
    pytest.param('regular_ll_msl', marks=pytest.mark.xfail),
    pytest.param('scanning_mode_64', marks=pytest.mark.xfail),
    pytest.param('spherical_harmonics', marks=pytest.mark.xfail),
    pytest.param('t_analysis_and_fc_0', marks=pytest.mark.xfail),
])
def test_to_grib_eccodes(grib_name, tmpdir):
    grib_path = os.path.join(SAMPLE_DATA_FOLDER, grib_name + '.grib')
    out_path = str(tmpdir.join(grib_name + '.grib'))

    res = xarray_store.open_dataset(grib_path, flavour_name='eccodes', cache=False)

    xarray_to_grib.canonical_dataset_to_grib(res, out_path)
    reread = xarray_store.open_dataset(out_path, flavour_name='eccodes', cache=False)
    assert res.equals(reread)


@pytest.mark.parametrize('grib_name', [
    'era5-levels-members',
    pytest.param('hpa_and_pa', marks=pytest.mark.xfail),
    pytest.param('fields_with_missing_values', marks=pytest.mark.xfail),
    pytest.param('lambert_grid', marks=pytest.mark.xfail),
    pytest.param('reduced_gg', marks=pytest.mark.xfail),
    pytest.param('regular_gg_sfc', marks=pytest.mark.xfail),
    pytest.param('regular_gg_pl', marks=pytest.mark.xfail),
    pytest.param('regular_gg_ml', marks=pytest.mark.xfail),
    pytest.param('regular_gg_ml_g2', marks=pytest.mark.xfail),
    'regular_ll_sfc',
    'regular_ll_msl',
    'scanning_mode_64',
    pytest.param('spherical_harmonics', marks=pytest.mark.xfail),
    't_analysis_and_fc_0',
])
def test_to_grib_ecmwf(grib_name, tmpdir):
    grib_path = os.path.join(SAMPLE_DATA_FOLDER, grib_name + '.grib')
    out_path = str(tmpdir.join(grib_name + '.grib'))

    res = xarray_store.open_dataset(grib_path, cache=False)

    xarray_to_grib.canonical_dataset_to_grib(res, out_path)
    reread = xarray_store.open_dataset(out_path, cache=False)
    assert res.equals(reread)
