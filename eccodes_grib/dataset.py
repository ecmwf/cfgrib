#
# Copyright 2017-2018 B-Open Solutions srl.
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
from builtins import object

import functools
import logging
import typing as T  # noqa

import attr

from . import eccodes
from . import messages

LOG = logging.getLogger(__name__)


def cached(method):
    # type: (T.Callable) -> T.Callable
    @functools.wraps(method)
    def cached_method(self):
        cache_name = '_' + method.__name__
        if not hasattr(self, cache_name):
            setattr(self, cache_name, method(self))
        return getattr(self, cache_name)
    return cached_method


@attr.attrs()
class Variable(object):
    name = attr.attrib()
    paramId = attr.attrib()


EXCLUDES = ('latitudes', 'latLonValues', 'longitudes', 'values', '7777')


def index_file(stream, includes=None, excludes=EXCLUDES, log=LOG):
    # type: (messages.Stream, T.Iterable[str], T.Iterable[str], logging.Logger) -> list
    index = []
    includes_set = set(includes) if includes else None
    excludes_set = set(excludes)
    for msg in stream:
        index_keys = {}
        for key in msg:
            if (includes_set is None or key in includes_set) and key not in excludes_set:
                try:
                    value = msg[key]
                    if isinstance(value, list):
                        value = tuple(value)
                    index_keys[key] = value
                except (TypeError, eccodes.EcCodesError):
                    log.info('Skipping %r', key)
        index.append((msg.offset, index_keys))
    return index


@attr.attrs()
class Dataset(object):
    path = attr.attrib(type=str)
    mode = attr.attrib(default='r')

    def __attrs_post_init__(self):
        self.stream = messages.Stream(self.path, mode=self.mode)

    @property
    @cached
    def variables(self):
        index = self.stream.index(['paramId'])
        variables = {}
        for param_id in index['paramId']:
            msg = next(iter(index.select({'paramId': param_id})))
            name = msg.get('shortName', 'paramId%s' % param_id)
            variables[name] = Variable(name=name, paramId=param_id)
        return variables