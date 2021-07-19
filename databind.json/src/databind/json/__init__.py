
__author__ = 'Niklas Rosenstein <rosensteinniklas@gmail.com>'
__version__ = '0.12.0'

import datetime
import decimal
import io
import json
import typing as t
from nr.parsing.date import duration
from databind.core.objectmapper import ObjectMapper, SimpleModule
from databind.core.types import ListType, MapType, ObjectType, OptionalType, SetType, UnionType
from .modules.optional import OptionalConverter
from .modules.collection import CollectionConverter
from .modules.datetime import DatetimeJsonConverter, DurationConverter
from .modules.decimal import DecimalJsonConverter
from .modules.map import MapConverter
from .modules.object import ObjectTypeConverter
from .modules.plain import PlainJsonConverter
from .modules.union import UnionConverter

__all__ = [
  'JsonModule',
]

T = t.TypeVar('T')
JsonType = t.Union[t.Mapping, t.Collection, str, int, float, bool, None]


class JsonModule(SimpleModule):
  """
  A composite of all modules for JSON de/serialization.
  """

  def __init__(self, name: str = None) -> None:
    super().__init__(name)

    self.add_converter_for_type(ObjectType, ObjectTypeConverter())
    self.add_converter_for_type(UnionType, UnionConverter())
    self.add_converter_for_type(bool, PlainJsonConverter())
    self.add_converter_for_type(float, PlainJsonConverter())
    self.add_converter_for_type(int, PlainJsonConverter())
    self.add_converter_for_type(str, PlainJsonConverter())
    self.add_converter_for_type(decimal.Decimal, DecimalJsonConverter())
    self.add_converter_for_type(datetime.date, DatetimeJsonConverter())
    self.add_converter_for_type(datetime.time, DatetimeJsonConverter())
    self.add_converter_for_type(datetime.datetime, DatetimeJsonConverter())
    self.add_converter_for_type(duration, DurationConverter())
    self.add_converter_for_type(OptionalType, OptionalConverter())
    self.add_converter_for_type(MapType, MapConverter())
    self.add_converter_for_type(ListType, CollectionConverter())
    self.add_converter_for_type(SetType, CollectionConverter())


def new_mapper() -> ObjectMapper:
  return ObjectMapper.default(JsonModule(), name=__name__)


def load(
  data: t.Union[JsonType, t.TextIO],
  type_: t.Type[T],
  mapper: ObjectMapper = None,
  filename: str = None,
  annotations: t.List[t.Any] = None,
  options: t.List[t.Any] = None,
) -> T:

  if hasattr(data, 'read'):
    if not filename:
      filename = getattr(data, 'name', None)
    data = json.load(data)
  return (mapper or new_mapper()).deserialize(data, type_, filename=filename, annotations=annotations, options=options)


def loads(
  data: str,
  type_: t.Type[T],
  mapper: ObjectMapper = None,
  filename: str = None,
  annotations: t.List[t.Any] = None,
  options: t.List[t.Any] = None,
) -> T:
  return load(io.StringIO(data), type_, mapper, filename, annotations, options)


def dump(
  value: T,
  type_: t.Type[T] = None,
  mapper: ObjectMapper = None,
  annotations: t.List[t.Any] = None,
  options: t.List[t.Any] = None,
  out: t.TextIO = None,
) -> JsonType:

  data = (mapper or new_mapper()).serialize(value, type_ or type(value), annotations=annotations, options=options)
  if out is not None:
    json.dump(data, out)
  return data


def dumps(
  value: T,
  type_: t.Type[T] = None,
  mapper: ObjectMapper = None,
  annotations: t.List[t.Any] = None,
  options: t.List[t.Any] = None,
) -> str:
  return json.dumps(dump(value, type_, mapper, annotations, options))
