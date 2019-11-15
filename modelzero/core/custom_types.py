
import datetime
from modelzero.core.types import Type

class MZTypes:
    Int = Type.as_opaque_type("int", int)
    Long = Type.as_opaque_type("long", int)
    String = Type.as_opaque_type("str", str)
    Bytes = Type.as_opaque_type("bytes", bytes)
    URL = Type.as_opaque_type("URL", str)
    Bool = Type.as_opaque_type("bool", bool)
    Float = Type.as_opaque_type("float", float)
    Double = Type.as_opaque_type("double", float)
    List = Type.as_opaque_type("list", list)
    Map = Type.as_opaque_type("map", map)
    Key = Type.as_opaque_type("key")
    DateTime = Type.as_opaque_type("DateTime", datetime.datetime)
    Optional = Type.as_opaque_type("Optional")

class CTypes:
    UInt8 = Type.as_opaque_type("uint8")
    UInt16 = Type.as_opaque_type("uint16")
    UInt32 = Type.as_opaque_type("uint32")
    UInt64 = Type.as_opaque_type("uint64")
    Int8 = Type.as_opaque_type("int8")
    Int16 = Type.as_opaque_type("int16")
    Int32 = Type.as_opaque_type("int32")
    Int64 = Type.as_opaque_type("int64")
    Float = Type.as_opaque_type("float")
    Double = Type.as_opaque_type("double")
    String = Type.as_opaque_type("string")
    Bool = Type.as_opaque_type("bool")

class KotlinTypes:
    Int = Type.as_opaque_type("int", int)
    Long = Type.as_opaque_type("long", int)
    String = Type.as_opaque_type("str", str)
    Bytes = Type.as_opaque_type("bytes", bytes)
    URL = Type.as_opaque_type("URL", str)
    Bool = Type.as_opaque_type("bool", bool)
    Float = Type.as_opaque_type("float", float)
    Double = Type.as_opaque_type("double", float)
    List = Type.as_opaque_type("list", list)
    Map = Type.as_opaque_type("map", map)
    Key = Type.as_opaque_type("key")
    DateTime = Type.as_opaque_type("DateTime", datetime.datetime)
    Optional = Type.as_opaque_type("Optional")
