
import abc
import enum
import typing as t
from dataclasses import dataclass, field

from databind.core.schema import Field
from .annotations import Annotation, get_annotation
from .location import Location, Position
from .typehint import TypeHint

T_Annotation = t.TypeVar('T_Annotation', bound=Annotation)


class Direction(enum.Enum):
  """
  Encodes the conversion direction in a #ConversionEnv.
  """

  #: Conversion takes place from some data format to a Python object.
  deserialize = enum.auto()

  #: Conversion takes place from a Python object to another data format.
  serialize = enum.auto()


class IConverter(metaclass=abc.ABCMeta):
  """
  Interface for deserializers and serializers.
  """

  @abc.abstractmethod
  def convert(self, ctx: 'Context') -> t.Any: ...


class IConverterProvider(metaclass=abc.ABCMeta):
  """
  Provider for an #IConverter for a #TypeHint.
  """

  @abc.abstractmethod
  def get_converter(self, type: TypeHint, direction: 'Direction') -> IConverter: ...

  Wrapper: t.Type['_ConverterProviderWrapper']


class IAnnotationsProvider(metaclass=abc.ABCMeta):
  """
  Interface to provide annotations for a given type or field in a type.
  """

  @abc.abstractmethod
  def get_global_annotation(self, annotation_cls: t.Type[T_Annotation]) -> t.Optional[T_Annotation]:
    ...

  @abc.abstractmethod
  def get_type_annotation(self,
      type: t.Type,
      annotation_cls: t.Type[T_Annotation]
  ) -> t.Optional[T_Annotation]:
    ...

  @abc.abstractmethod
  def get_field_annotation(self,
      type: t.Type,
      field_name: str,
      annotation_cls: t.Type[T_Annotation]
  ) -> t.Optional[T_Annotation]:
    ...


class ITypeHintAdapter(metaclass=abc.ABCMeta):
  """
  The #ITypeAdapter has a chance to alter a #TypeHint before it is used to look up an #IConverter
  via an #IConverterProvider.
  """

  @abc.abstractmethod
  def adapt_type_hint(self, type: TypeHint) -> TypeHint: ...


class IObjectMapper(IAnnotationsProvider, IConverterProvider, ITypeHintAdapter):
  """
  An object mapper is a combination of various interfaces that are required during the
  de/serialization process.
  """


@dataclass
class Context:
  """
  Container for the information that is passed to an #IConverter for the de/serialization of a
  value (as denoted by the #direction). Converters may create a new #Context object referencing
  the original context in the #parent field to kick off the de/serialization of a sub value.
  """

  #: Reference to the parent #Value object.
  parent: t.Optional['Context']

  #: The object mapper that is used to convert the value.
  mapper: IObjectMapper

  #: The direction of the conversion.
  direction: Direction

  #: The value that is de/serialized in this context.
  value: t.Any

  #: The location of the value in the source data. This contains the type information for
  #: the #value, which is also accesible via #type.
  location: Location

  #: The #Field data from the schema that the value is de/serialized from/to. Can be used to
  #: read annotations that influence the conversion behaviour. Note that the #Field.type
  #: may be different from the #Location.type if the de/serialization is executed on a field
  #: representing a complex type (e.g., a list or map).
  field: Field

  def __str__(self) -> str:
    return f'Context(direction={self.direction.name}, value={_trunc(repr(self.value), 30)})'

  @property
  def type(self) -> TypeHint:
    return self.location.type

  def push(self,
    type: TypeHint,
    value: t.Any,
    key: t.Union[str, int, None],
    field: t.Optional[Field] = None,
    filename: t.Optional[str] = None,
    position: t.Optional[Position] = None
  ) -> 'Context':
    location = self.location.push(type, key, filename, position)
    return Context(self, self.mapper, self.direction, value, location, field or Field(type, []))

  def convert(self) -> t.Any:
    return self.mapper.get_converter(self.location.type, self.direction).convert(self)

  def get_annotation(self, annotation_cls: t.Type[T_Annotation]) -> t.Optional[T_Annotation]:
    return get_annotation(self.field.annotations, annotation_cls, None) or \
      self.mapper.get_global_annotation(annotation_cls)

  def error(self, message: str) -> 'ConversionError':
    return ConversionError(message, self.location)

  def type_error(self, *, expected: t.Union[str, t.Type, t.Tuple[t.Type, ...]]) -> 'ConversionError':
    if isinstance(expected, tuple):
      expected = '|'.join(x.__name__ for x in expected)
    elif isinstance(expected, type):
      expected = expected.__name__
    return self.error(
      f'expected {expected} to {self.direction.name.lower()} {self.type}, '
      f'got {type(self.value).__name__}')


@dataclass
class ConverterNotFound(Exception):
  type: TypeHint
  direction: Direction


@dataclass
class ConversionError(Exception):
  message: t.Union[str, Exception]
  location: Location

  def __str__(self) -> str:
    return f'{self.location}: {self.message}'


class _ConverterProviderWrapper(IConverterProvider):

  def __init__(self, func: t.Callable[[TypeHint], IConverter]) -> None:
    self._func = func

  def get_converter(self, type: TypeHint, direction: 'Direction') -> IConverter:
    return self._func(type, direction)  # type: ignore


IConverterProvider.Wrapper = _ConverterProviderWrapper


def _trunc(s: str, l: int) -> str:
  if len(s) > l:
    return s[:l] + '... '
  return s
