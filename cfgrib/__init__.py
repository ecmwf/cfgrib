#
# Copyright 2017-2021 European Centre for Medium-Range Weather Forecasts (ECMWF).
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

__version__ = "0.9.10.4"

# cfgrib core API depends on the ECMWF ecCodes C-library only
from .abc import Field, Fieldset, Index, MappingFieldset
from .cfmessage import COMPUTED_KEYS
from .dataset import (
    Dataset,
    DatasetBuildError,
    compute_index_keys,
    open_fieldset,
    open_file,
    open_from_index,
)
from .messages import FieldsetIndex, FileStream, Message

# NOTE: xarray is not a hard dependency, but let's provide helpers if it is available.
try:
    from .xarray_store import open_dataset, open_datasets
except ImportError:
    pass
