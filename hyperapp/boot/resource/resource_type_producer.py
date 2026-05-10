
def resource_type_producer(resource_type_factory, type_to_resource_type, resource_t):
    try:
        return type_to_resource_type[resource_t]
    except KeyError:
        return resource_type_factory(resource_t)
