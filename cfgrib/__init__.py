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

from __future__ import absolute_import, division, print_function, unicode_literals

# cfgrib core API depends on the ECMWF ecCodes C-library only

from .cfmessage import CfMessage
from .dataset import Dataset, DatasetBuildError, open_file
from .messages import Message, FileStream

__all__ = ['CfMessage', 'Dataset', 'DatasetBuildError', 'FileStream', 'Message', 'open_file']

# NOTE: xarray is not a hard dependency, but let's provide helpers if it is available.

try:
    from .xarray_store import open_dataset
    from .xarray_to_grib import canonical_dataset_to_grib, to_grib

    __all__ += ['canonical_dataset_to_grib', 'open_dataset', 'to_grib']
except ImportError:
    pass
