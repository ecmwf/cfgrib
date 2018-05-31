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
    pass


EXCLUDES = ('latitudes', 'longitudes', 'values', '7777')


def index_file(file, includes=None, excludes=EXCLUDES, log=LOG):
    # type: (messages.File, T.Iterable[str], T.Iterable[str], logging.Logger) -> T.Dict[str, T.Any]
    index = {}
    includes_set = set(includes) if includes else None
    excludes_set = set(excludes)
    with file as stream:
        for msg in stream:
            for key in msg:
                if (includes_set is None or key in includes_set) and key not in excludes_set:
                    try:
                        value = msg[key]
                        if isinstance(value, list):
                            value = tuple(value)
                        index.setdefault(key, set()).add(value)
                    except TypeError:
                        log.warning('Skipping %r', key)
    return index


@attr.attrs()
class Dataset(object):
    filename = attr.attrib(type=str)
    mode = attr.attrib(default='r')
    file = attr.attrib(default=None, init=False)

    def __attrs_post_init__(self):
        self.file = messages.File(self.filename, mode=self.mode)
        self.index = index_file(self.file)
        self.attrs = {k: v.pop() for k, v in self.index.items() if len(v) == 1 and None not in v}

    @property
    @cached
    def variables(self):
        return {}
