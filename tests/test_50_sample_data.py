
import os.path

import pytest

from cfgrib import xarray_store

SAMPLE_DATA_FOLDER = os.path.join(os.path.dirname(__file__), 'sample-data')


@pytest.mark.parametrize('grib_name', [
    'era5-levels-members',
    pytest.mark.xfail('hpa_and_pa'),
    'fields_with_missing_values',
    'lambert_grid',
    pytest.mark.xfail('reduced_gg'),
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
    'uv_on_different_levels',
])
def test_open_dataset_fail(grib_name):
    grib_path = os.path.join(SAMPLE_DATA_FOLDER, grib_name + '.grib')
    with pytest.raises(ValueError):
        xarray_store.open_dataset(grib_path, cache=False)
