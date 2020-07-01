#
# Copyright 2017-2020 European Centre for Medium-Range Weather Forecasts (ECMWF).
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
# Authors:
#   Alessandro Amici - B-Open - https://bopen.eu
#

import os.path

import click

# NOTE: imports are executed inside functions so missing dependencies don't break all commands


@click.group()
def cfgrib_cli():
    pass


@cfgrib_cli.command('selfcheck')
def selfcheck():
    from .messages import eccodes_version

    print("Found: ecCodes v%s." % eccodes_version)
    print("Your system is ready.")


@cfgrib_cli.command('to_netcdf')
@click.argument('inpaths', nargs=-1)
@click.option('--outpath', '-o', default=None)
@click.option('--cdm', '-c', default=None)
@click.option('--engine', '-e', default='cfgrib')
def to_netcdf(inpaths, outpath, cdm, engine):
    import cf2cdm
    import xarray as xr

    # NOTE: noop if no input argument
    if len(inpaths) == 0:
        return

    if not outpath:
        outpath = os.path.splitext(inpaths[0])[0] + '.nc'

    ds = xr.open_mfdataset(inpaths, engine=engine, combine='by_coords')
    if cdm:
        coord_model = getattr(cf2cdm, cdm)
        ds = cf2cdm.translate_coords(ds, coord_model=coord_model)
    ds.to_netcdf(outpath)


if __name__ == '__main__':  # pragma: no cover
    cfgrib_cli()
