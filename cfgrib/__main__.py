#
# Copyright 2017-2018 European Centre for Medium-Range Weather Forecasts (ECMWF).
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

from . import eccodes


@click.group()
def cfgrib_cli():
    pass


@cfgrib_cli.command('selfcheck')
def selfcheck():
    print("Found: ecCodes v%s." % eccodes.codes_get_api_version())
    print("Your system is ready.")


@cfgrib_cli.command('to_netcdf')
@click.argument('inpath')
@click.option('--outpath', '-o', default=None)
def to_netcdf(inpath, outpath):
    import xarray as xr

    if not outpath:
        outpath = os.path.splitext(inpath)[0] + '.nc'

    ds = xr.open_dataset(inpath, engine='cfgrib')
    ds.to_netcdf(outpath)


if __name__ == '__main__':  # pragma: no cover
    cfgrib_cli()
