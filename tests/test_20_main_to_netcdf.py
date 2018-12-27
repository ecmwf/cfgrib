
import os.path

import click.testing
import pytest

dask = pytest.importorskip('dask')  # noqa
xr = pytest.importorskip('xarray')  # noqa

from cfgrib import __main__

SAMPLE_DATA_FOLDER = os.path.join(os.path.dirname(__file__), 'sample-data')
TEST_DATA = os.path.join(SAMPLE_DATA_FOLDER, 'era5-levels-members.grib')


def test_cfgrib_cli_to_netcdf():
    runner = click.testing.CliRunner()

    res = runner.invoke(__main__.cfgrib_cli, ['to_netcdf'])

    assert res.exit_code == 0
    assert res.output == ''

    res = runner.invoke(__main__.cfgrib_cli, ['to_netcdf', TEST_DATA])

    assert res.exit_code == 0
    assert res.output == ''
