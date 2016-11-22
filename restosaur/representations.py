import traceback

from .utils import Collection, join_content_type_with_vnd
from . import serializers


class RepresentationAlreadyRegistered(Exception):
    pass


class UnknownRepresentation(Exception):
    pass


class ValidatorAlreadyRegistered(Exception):
    pass


def _pass_through_trasnform(x, ctx):
    return x


def _pass_through_validation(x, ctx):
    return x


class Representation(object):
    def __init__(
            self, vnd=None, content_type='application/json', qvalue=None,
            serializer=None, _transform_func=None):

        self.qvalue = qvalue if qvalue is not None else 1
        self.serializer = serializer or serializers.get(content_type)
        self.content_type = content_type
        self.vnd = vnd
        self._transform_func = _transform_func or _pass_through_trasnform

    def render(self, context, obj):
        """
        Renders representation of `obj` as raw content
        """
        if isinstance(obj, Collection):
            items = map(
                lambda x: self._transform_func(x, context), obj.iterable)
            data = {
                    obj.key: list(items),
                    obj.totalcount_key: len(obj.iterable),
                    }
        else:
            data = self._transform_func(obj, context)
        return self.serializer.dumps(data)

    def media_type(self):
        mt = join_content_type_with_vnd(self.content_type, self.vnd)
        return '%s; q=%s' % (mt, self.qvalue)


class Validator(object):
    def __init__(
            self, vnd=None, content_type='application/json',
            serializer=None, _validator_func=None):

        self.serializer = serializer or serializers.get(content_type)
        self.content_type = content_type
        self.vnd = vnd
        self._validator_func = _validator_func or _pass_through_validation

    def parse(self, context):
        """
        Parses raw representation content and builds object
        """
        return self._validator_func(self.serializer.loads(context), context)


class RestosaurExceptionDict(dict):
    def __init__(self, ex, tb=None):
        super(RestosaurExceptionDict, self).__init__()
        self.exc_type = type(ex)
        self.exc_value = ex
        self.tb = tb
        self.status_code = 500


def restosaur_exception_dict_as_text(obj, ctx):
    output = u'\n'.join(
            traceback.format_exception(obj.exc_type, obj.exc_value, obj.tb))

    return output
