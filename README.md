# Constraints

## Introduction

### Pros

- Flexible validation of Python objects.
- Validators return all violations, instead of only the first.
- Automatically derive constraints from SQLAlchemy models.
- Errors have a uniform format.

### Cons

- More queries than hand-crafted validation (this might be improved, but that is non-trivial).
- Less flexible (but also less room for mistakes and divergence).

## Example

To create and run a validator from a SQLAlchemy model `Child`, where `session`
is a database session, and `obj` is the object to validate.

```python
>>> from constraints.declarative import ToModel
>>> cn = ToModel(Child)
>>> cn.check(obj, session=session)
```

## Setup

Clone this repository, and run `make` for a set of options. To build the Sphinx documentation:

```
make build-docs
```
