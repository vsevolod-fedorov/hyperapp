from .services import (
    web,
    )


# Resource name actors: (piece, name_of) -> base resource name, without project and path.
# name_of maps an element piece to its own base name.


def python_module_resource_name(piece, name_of):
    return f'{piece.module_name}.module'


def attribute_resource_name(piece, name_of):
    # Always prefixed by the object name, module attributes too, so object type does not matter.
    # Drop object kind suffix: 'some_module.module' -> 'some_module', 'some_module.SomeClass.attr' -> 'some_module.SomeClass'.
    object_name, _ = name_of(web.summon(piece.object)).rsplit('.', 1)
    return f'{object_name}.{piece.attr_name}.attr'
