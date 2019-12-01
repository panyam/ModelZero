# ModelZero Type System

ModelZero allows easy specification of types so that apps are developed based on a foundation of strong and higher order types.

## Type Hierarchy

The type system in ModelZero is simple:

```
Type ::= opaque_type	# Named (native/opaque) types
	|	record_type		# tagged product types
    | 	union_type		# tagged union types
    |	sum_type		# untagged sum types
    |	tuple_type		# untagged product types
    |	type_var		# Type variables (not yet used)
    |	type_ref		# Types referenced by name.
    |	func_type		# Function types
    |	type_app		# Type applications
```

Each of these are described below

### Opaque Types

In ModelZero there are no "predefined" types like in other systems.  To define a type, simply create one.  eg:

```
Int = Type.as_opaque_type("Int")
```

Defines a new Int type.  A "native" type could also be associated with an opaque type:

```
Int = Type.as_opaque_type("Int", int)
```

other examples:

```
String = Type.as_opaque_type("String", str)
Float = Type.as_opaque_type("Float", float)
```

### Record Types

Record types allow the modelling of objects, records and structs common in most languages.  A record type simply looks like:

```
record_type ::= Field *

Field ::= name field_type optional?
```


### Union Types

Union types allow modelli
