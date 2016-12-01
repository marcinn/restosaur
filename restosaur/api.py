from collections import defaultdict

import six

from .representations import (
        RepresentationAlreadyRegistered, UnknownRepresentation,
        Representation, RestosaurExceptionDict,
        restosaur_exception_dict_as_text)
from .resource import Resource
from .utils import autodiscover, join_content_type_with_vnd
from .loading import load_resource
from .context import Context


class ModelViewAlreadyRegistered(Exception):
    pass


class ModelViewNotRegistered(Exception):
    pass


class BaseAPI(object):
    def __init__(
            self, path=None, middlewares=None,
            context_class=None, default_charset=None, debug=False):
        path = path or ''
        if path and not path.endswith('/'):
            path += '/'
        if path and path.startswith('/'):
            path = path[1:]
        self.path = path
        self.debug = debug
        self.resources = []
        self.default_charset = default_charset or 'utf-8'
        self.middlewares = middlewares or []
        self._representations = defaultdict(dict)  # type->repr_key
        self._model_views = defaultdict(dict)
        self.context_class = context_class or Context

    def make_context(self, **kwargs):
        return self.context_class(self, **kwargs)

    def add_resources(self, *resources):
        self.resources += resources

    def resource(self, path, *args, **kw):
        obj = Resource(self, path, *args, **kw)
        self.add_resources(obj)
        return obj

    def add_representation(
            self, type_, content_type, vnd=None, qvalue=None,
            serializer=None, _transform_func=None):

        representation = Representation(
            content_type=content_type, vnd=vnd,
            serializer=serializer, _transform_func=_transform_func,
            qvalue=qvalue)

        self.register_representation(type_, representation)

    def register_representation(self, type_, representation):

        content_type = representation.content_type
        vnd = representation.vnd
        repr_key = join_content_type_with_vnd(content_type, vnd)

        if (repr_key in self._representations and
                type_ in self._representations[repr_key]):
            raise RepresentationAlreadyRegistered(
                            '%s for %s' % (repr_key, type_))

        self._representations[repr_key][type_] = representation

    def get_representation(self, model, media_type):
        try:
            return self._representations[media_type][model]
        except KeyError:
            raise UnknownRepresentation('%s for %s' % (
                        media_type, model))

    def has_representation_for(self, model, media_type):
        return (media_type in self._representations
                and model in self._representations[media_type])

    @property
    def representations(self):
        result = []
        for models in self._representations.values():
            result += models.values()
        return result

    def resource_for_viewmodel(self, model, view_name=None):
        try:
            model_meta = self._model_views[model]
        except KeyError:
            raise ModelViewNotRegistered(
                    'No views are registered for %s' % model)

        try:
            resource = model_meta[view_name]
        except KeyError:
            if not view_name:
                raise ModelViewNotRegistered(
                    'No default view registered for %s' % model)
            else:
                raise ModelViewNotRegistered(
                    'View `%s` is not registered for %s' % (view_name, model))
        else:
            if isinstance(resource, six.string_types):
                resource = load_resource(resource)
                model_meta[view_name] = resource
            return resource

    def register_view(self, model, resource, view_name=None):
        if view_name in self._model_views[model]:
            if view_name:
                raise ModelViewAlreadyRegistered(
                    '%s is already registered as a "%s" view' % (
                        model, view_name))
            else:
                raise ModelViewAlreadyRegistered(
                    '%s is already registered as a default view' % model)

        self._model_views[model][view_name] = resource

    def view(self, resource, view_name=None):
        """
        A shortcut decorator for registering a `model_class`
        as as a `view_name` view of a `resource`.

        The `resource` may be passed as a dotted string path
        to avoid circular import problems.
        """

        def register_view_for_model(model_class):
            self.register_view(
                model_class, resource=resource, view_name=view_name)
            return model_class
        return register_view_for_model

    def autodiscover(self, *args, **kw):
        """
        Shortcut for `restosaur.autodiscover()`
        """
        autodiscover(*args, **kw)


class API(BaseAPI):
    def __init__(self, *args, **kw):
        super(API, self).__init__(*args, **kw)

        # backward compatibility
        configure_plain_text_api(self)
        configure_json_api(self)


JSON = API


def configure_json_api(api):
    api.add_representation(
            RestosaurExceptionDict, content_type='application/json')
    api.add_representation(
            dict, content_type='application/json')

    # backward compatibility

    from .utils import Collection
    api.add_representation(
            Collection, content_type='application/json')


def configure_plain_text_api(api):
    api.add_representation(
            RestosaurExceptionDict, content_type='text/plain',
            _transform_func=restosaur_exception_dict_as_text,
            qvalue=0.1)


def api_factory(path=None, api_class=API, **kwargs):
    api = api_class(path, **kwargs)
    return api


def json_api_factory(path=None, api_class=API, **kwargs):
    api = api_factory(path=path, api_class=api_class, **kwargs)
    return api
