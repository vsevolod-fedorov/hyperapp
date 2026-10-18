from .services import (
    web,
    )


def resource_name_creg(config, system_code_registry_factory):
    return system_code_registry_factory('resource_name_creg', config)


class _Namer:

    def __init__(self, resource_name_creg, pick_refs, known_names, resource_locations):
        self._resource_name_creg = resource_name_creg
        self._pick_refs = pick_refs
        self._piece_to_known_name = {}
        # A piece may be defined under several names; any one of them will do.
        for name_tuple, piece in known_names.items():
            project_name, path, name = name_tuple
            if (project_name, path) in resource_locations:
                continue  # That resource file is to be replaced, along with all its names.
            self._piece_to_known_name.setdefault(piece, name_tuple)
        self._piece_to_location = {
            piece: location
            for location, piece in resource_locations.items()
            }
        self._piece_to_name = {}
        self._name_to_piece = {}

    def name_all(self):
        for piece, location in self._piece_to_location.items():
            self._name(piece, location)
        return {**self._piece_to_known_name, **self._piece_to_name}

    def _name(self, piece, referrer_location):
        try:
            return self._piece_to_name[piece]
        except KeyError:
            pass
        # A piece placed into a resource file is always (re)named there,
        # even if loaded under some name: it replaces what was loaded from that file.
        try:
            location = self._piece_to_location[piece]
        except KeyError:
            try:
                return self._piece_to_known_name[piece]
            except KeyError:
                pass
            # An unnamed element goes to the same resource file as the piece referring it.
            location = referrer_location
        project_name, path = location
        # Name all elements, not only those the derived name depends on.
        for ref in self._pick_refs(piece):
            self._name(web.summon(ref), location)
        base_name = self._resource_name_creg.animate(piece, self._name_of_fn(location))
        name_tuple = (project_name, path, base_name)
        # No numbered suffixes to disambiguate: a clash means an actor should derive a more specific name.
        other_piece = self._name_to_piece.setdefault(name_tuple, piece)
        if other_piece != piece:
            raise RuntimeError(
                f"Name {project_name}:{'/'.join(path)}:{base_name} is derived for two pieces:"
                f" {other_piece!r} and {piece!r}")
        self._piece_to_name[piece] = name_tuple
        return name_tuple

    def _name_of_fn(self, location):
        def name_of(piece):
            _, _, base_name = self._name(piece, location)
            return base_name
        return name_of


# Give names to resources placed into resource files, and to their unnamed elements.
# known_names: (project_name, path, name) -> piece, as returned by resource loader.
# resource_locations: (project_name, path) -> piece, a resource file and its main piece.
# Returns piece -> (project_name, path, name), for known and newly named pieces.
def name_resources(resource_name_creg, pick_refs, known_names, resource_locations):
    namer = _Namer(resource_name_creg, pick_refs, known_names, resource_locations)
    return namer.name_all()
