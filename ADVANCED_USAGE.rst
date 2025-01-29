
ECMWF’s MARS and Metview software introduced the notion of *Fieldset* which is an
ordered collection of GRIB message. The *Fieldset* is an abstract concept and can be
implemented in many ways. In the case of MARS and Metview, a *Fieldset* is an implemented
internally as an array of *Field*, each *Field* being represented by a file path, an offset and a
length where the actual GRIB message can be found. Thus, a *Fieldset* can represent an
ordered collection of *Field* which are at various locations of several files.


*cfgrib* now provides the definition of a ``Field`` and ``Fieldset`` types in the ``cfgrib.abc`` module
and additionally a ``MappingFieldset`` for specialised use.
The implementations are based on simple python sequences and mappings so that *cfgrib*
can build a Dataset for example from something as simple as a list of dicts.

Classes that implement the ``Fieldset`` and the ``MappingFieldset`` interface
can use the low-level interface ``cfgrib.open_fielset`` to obtain a ``cfgrib.Dataset``
or they can be passed directly to *Xarray*.


The simplest *Fieldset* is a list of dictionaries:

.. code-block:: python

    >>> import xarray as xr
    >>> fieldset = [
    ...     {
    ...         "gridType": "regular_ll",
    ...         "Nx": 2,
    ...         "Ny": 3,
    ...         "distinctLatitudes": [-10.0, 0.0, 10.0],
    ...         "distinctLongitudes": [0.0, 10.0],
    ...         "paramId": 130,
    ...         "shortName": "t",
    ...         "values": [[1, 2], [3, 4], [5, 6]],
    ...         "dataDate": 20211216,
    ...         "dataTime": 1200,
    ...     }
    ... ]
    >>> ds = xr.open_dataset(fieldset, engine="cfgrib")
    >>> ds
    <xarray.Dataset>
    Dimensions:    (latitude: 3, longitude: 2)
    Coordinates:
        time       datetime64[ns] ...
    * latitude   (latitude) float64 -10.0 0.0 10.0
    * longitude  (longitude) float64 0.0 10.0
    Data variables:
        t          (latitude, longitude) float32 ...
    Attributes:
        Conventions:  CF-1.7
        history:      ...
    >>> ds.mean()
    <xarray.Dataset>
    Dimensions:  ()
    Coordinates:
        time     datetime64[ns] ...
    Data variables:
        t        float32 3.5


For example you can implement a dedicated ``Fieldset`` class following this pattern:

.. code-block:: python

    from typing import Iterator

    from cfgrib import abc

    class MyFieldset(abc.Fieldset):
        def __len__(self) -> int:  # not used by cfgrib
            ...
        def __getitem__(self, item: int) -> abc.Field:
            ...
        def __iter__(self) -> Iterator[abc.Field]:
            ...


If ``__getitem__`` and ``__iter__`` implement lazy loading of GRIB fields *cfgrib* and
*Xarray* will be able to access larger-than-memory files.

In the event a ``Field`` is identified by a more complex *key* than just an sequence *index*
developers may implemnt a ``MappingFieldset`` class following this pattern:

.. code-block:: python

    from typing import ItemsView, Iterator

    from cfgrib import abc

    class MyFieldset(abc.MappingFieldset[T.Any, abc.Field]):
        def __len__(self) -> int:  # not used by cfgrib
            ...
        def __getitem__(self, item: int) -> abc.Field:
            ...
        def __iter__(self) -> Iterator[abc.Field]:  # not used by cfgrib
            ...
        def items() -> ItemsView[T.Any, abc.Field]:
            ...


Again if ``__getitem__`` and ``items`` implement lazy loading of GRIB fields *cfgrib* and
*Xarray* will be able to access larger-than-memory files.

An example of the ``MappingFieldset`` use is ``cfgrib.messages.FileStream`` that
uses the *file offset* as the *key*.
