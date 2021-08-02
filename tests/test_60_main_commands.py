import os.path

import click.testing
import py
import pytest

pytest.importorskip("scipy", reason="scpy not found")
xr = pytest.importorskip("xarray")  # noqa

from cfgrib import __main__

SAMPLE_DATA_FOLDER = os.path.join(os.path.dirname(__file__), "sample-data")
TEST_DATA = os.path.join(SAMPLE_DATA_FOLDER, "era5-levels-members.grib")


def test_cfgrib_cli_to_netcdf(tmpdir: py.path.local) -> None:
    runner = click.testing.CliRunner()

    res = runner.invoke(__main__.cfgrib_cli, ["to_netcdf"])

    assert res.exit_code == 0
    assert res.output == ""

    res = runner.invoke(__main__.cfgrib_cli, ["to_netcdf", TEST_DATA])

    assert res.exit_code == 0
    assert res.output == ""

    out = tmpdir.join("tmp.nc")
    res = runner.invoke(__main__.cfgrib_cli, ["to_netcdf", TEST_DATA, "-o" + str(out), "-cCDS"])

    assert res.exit_code == 0
    assert res.output == ""


def test_cfgrib_cli_dump() -> None:
    runner = click.testing.CliRunner()

    res = runner.invoke(__main__.cfgrib_cli, ["dump"])

    assert res.exit_code == 0
    assert res.output == ""

    res = runner.invoke(__main__.cfgrib_cli, ["dump", TEST_DATA])

    assert res.exit_code == 0
    assert "<xarray.Dataset" in res.output

    res = runner.invoke(__main__.cfgrib_cli, ["dump", TEST_DATA, "-vlat", "-cCDS"])

    assert res.exit_code == 0
    assert "<xarray.DataArray" in res.output
