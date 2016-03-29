from restosaur import API, urltemplate


class ResourceAlreadyRegistered(Exception):
    pass


def autogenerate_resource_name(resource):
    path = urltemplate.remove_parameters(resource.path)

    try:
        name = filter(None, path.split('/'))[-1]
    except IndexError:
        name = '/'

    return name


class ApiRoot(object):
    def __init__(self):
        self.resources = {}

    def register(self, resource, name=None):
        name = name or autogenerate_resource_name(resource)

        if name in self.resources:
            raise ResourceAlreadyRegistered(name)
        self.resources[name]=resource

    def expose(self, name, resource):
        def wrap(resource):
            self.register(resource, name)
            return resource
        return wrap

    def as_view(self):
        def get_api_root(ctx):
            data = {}

            for name, resource in self.resources.items():
                data[name]=resource.uri(ctx)

            return ctx.Entity(data)
        return get_api_root


