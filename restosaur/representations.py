from . import serializers


class RepresentationAlreadyRegistered(Exception):
    pass


def _pass_through_trasnform(x):
    return x


class Representation(object):
    links = {}

    def __init__(
            self, vnd=None, content_type='application/json', serializer=None,
            _transform_func=None):

        self.serializer = serializer or serializers.get(content_type)
        self.content_type = content_type
        self.vnd = vnd
        self._transform_func = _transform_func or _pass_through_trasnform

    def to_dict(self, obj):
        data = {}
        data.update(obj)
        data.update({
            '_links': self.links,
            })
        return data

    def render(self, context, obj):
        """
        Renders representation of `obj` as raw content
        """
        return self.serializer.dumps(self.to_dict(self._transform_func(obj)))

    def parse(self, context):
        """
        Parses raw representation content and builds object
        """
        return self.serializer.loads(context)
