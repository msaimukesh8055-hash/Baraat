"""A small JSON-Schema-subset validator (dependency-light, like Phase 1's validator).

Handles exactly the constructs our tool contracts use: type, required,
properties, additionalProperties (bool or sub-schema), enum, minimum/maximum/
exclusiveMinimum, minLength, minItems/maxItems, items. Returns a list of
human-readable error strings ([] == valid) so errors can feed a repair loop —
the same pattern as `src/extraction/validator.py`.

Deliberately not the `jsonschema` library: our schemas are small and fixed, and
staying dependency-free is a project convention (cf. the NumPy vector store).
"""


def _type_ok(value, t: str) -> bool:
    if t == "object":
        return isinstance(value, dict)
    if t == "array":
        return isinstance(value, list)
    if t == "string":
        return isinstance(value, str)
    if t == "boolean":
        return isinstance(value, bool)
    if t == "integer":
        return isinstance(value, int) and not isinstance(value, bool)
    if t == "number":
        return isinstance(value, (int, float)) and not isinstance(value, bool)
    return True


def validate_against_schema(data, schema: dict, path: str = "") -> list[str]:
    errors: list[str] = []
    here = path or "value"

    t = schema.get("type")
    if t and not _type_ok(data, t):
        return [f"{here}: expected {t}, got {type(data).__name__}"]

    if "enum" in schema and data not in schema["enum"]:
        errors.append(f"{here}: {data!r} not one of {schema['enum']}")

    if t in ("number", "integer"):
        if "minimum" in schema and data < schema["minimum"]:
            errors.append(f"{here}: {data} < minimum {schema['minimum']}")
        if "maximum" in schema and data > schema["maximum"]:
            errors.append(f"{here}: {data} > maximum {schema['maximum']}")
        if "exclusiveMinimum" in schema and data <= schema["exclusiveMinimum"]:
            errors.append(f"{here}: {data} must be > {schema['exclusiveMinimum']}")

    if t == "string" and "minLength" in schema and len(data) < schema["minLength"]:
        errors.append(f"{here}: string shorter than {schema['minLength']}")

    if t == "array":
        if "minItems" in schema and len(data) < schema["minItems"]:
            errors.append(f"{here}: fewer than {schema['minItems']} items")
        if "maxItems" in schema and len(data) > schema["maxItems"]:
            errors.append(f"{here}: more than {schema['maxItems']} items")
        item_schema = schema.get("items")
        if item_schema:
            for i, item in enumerate(data):
                errors += validate_against_schema(item, item_schema, f"{here}[{i}]")

    if t == "object":
        props = schema.get("properties", {})
        for req in schema.get("required", []):
            if req not in data:
                errors.append(f"{here}: missing required '{req}'")
        addl = schema.get("additionalProperties", True)
        for k, v in data.items():
            sub = f"{path}.{k}" if path else k
            if k in props:
                errors += validate_against_schema(v, props[k], sub)
            elif addl is False:
                errors.append(f"{sub}: unexpected property")
            elif isinstance(addl, dict):
                errors += validate_against_schema(v, addl, sub)

    return errors
