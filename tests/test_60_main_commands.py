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


def test_cfgrib_cli_to_netcdf_backend_kwargs(tmpdir: py.path.local) -> None:
    runner = click.testing.CliRunner()

    backend_kwargs = '{"time_dims": ["time"]}'
    res = runner.invoke(__main__.cfgrib_cli, ["to_netcdf", TEST_DATA, "-b", backend_kwargs])

    assert res.exit_code == 0
    assert res.output == ""

    backend_kwargs_json = tmpdir.join("temp.json")
    with open(backend_kwargs_json, "w") as f:
        f.write(backend_kwargs)
    res = runner.invoke(
        __main__.cfgrib_cli, ["to_netcdf", TEST_DATA, "-b", str(backend_kwargs_json)]
    )

    assert res.exit_code == 0
    assert res.output == ""


def test_cfgrib_cli_to_netcdf_netcdf_kwargs(tmpdir: py.path.local) -> None:
    runner = click.testing.CliRunner()

    netcdf_kwargs = '{"engine": "scipy"}'
    res = runner.invoke(__main__.cfgrib_cli, ["to_netcdf", TEST_DATA, "-n", netcdf_kwargs])

    assert res.exit_code == 0
    assert res.output == ""

    netcdf_kwargs_json = tmpdir.join("temp.json")
    with open(netcdf_kwargs_json, "w") as f:
        f.write(netcdf_kwargs)
    res = runner.invoke(
        __main__.cfgrib_cli, ["to_netcdf", TEST_DATA, "-n", str(netcdf_kwargs_json)]
    )

    assert res.exit_code == 0
    assert res.output == ""


def test_cfgrib_cli_to_netcdf_var_encoding(tmpdir: py.path.local) -> None:
    runner = click.testing.CliRunner()

    var_encoding = '{"dtype": "float", "scale_factor": 0.1}'
    res = runner.invoke(__main__.cfgrib_cli, ["to_netcdf", TEST_DATA, "-v", var_encoding])

    assert res.exit_code == 0
    assert res.output == ""

    var_encoding_json = tmpdir.join("temp.json")
    with open(var_encoding_json, "w") as f:
        f.write(var_encoding)
    res = runner.invoke(
        __main__.cfgrib_cli, ["to_netcdf", TEST_DATA, "-v", str(var_encoding_json)]
    )

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
