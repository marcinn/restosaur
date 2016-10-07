from collections import defaultdict
import six

from .representations import (
        RepresentationAlreadyRegistered, UnknownRepresentation,
        Representation)
from .resource import Resource
from .utils import autodiscover, join_content_type_with_vnd
from .loading import load_resource


class ModelViewAlreadyRegistered(Exception):
    pass


class ModelViewNotRegistered(Exception):
    pass


class API(object):
    def __init__(
            self, path=None, resources=None, middlewares=None,
            context_class=None, default_charset=None, debug=False):
        path = path or ''
        if path and not path.endswith('/'):
            path += '/'
        if path and path.startswith('/'):
            path = path[1:]
        self.path = path
        self.debug = debug
        self.resources = resources or []
        self.default_charset = default_charset or 'utf-8'
        self.middlewares = middlewares or []
        self._representations = defaultdict(dict)  # type->repr_key
        self._model_views = defaultdict(dict)
        self.context_class = context_class

    def add_resources(self, *resources):
        self.resources += resources

    def resource(self, *args, **kw):
        obj = Resource(self, *args, **kw)
        self.add_resources(obj)
        return obj

    def add_representation(
            self, type_, content_type, vnd=None,
            serializer=None, _transform_func=None):

        representation = Representation(
            content_type=content_type, vnd=vnd,
            serializer=serializer, _transform_func=_transform_func)

        self.register_representation(representation)

    def register_representation(self, type_, representation):

        content_type = representation.content_type
        vnd = representation.vnd
        repr_key = join_content_type_with_vnd(content_type, vnd)

        if repr_key in self._representations[type_]:
            raise RepresentationAlreadyRegistered(
                            '%s: %s' % (type_, repr_key))

        self._representations[type_][repr_key] = representation

    def get_representation(self, type_, content_type, vnd=None):
        repr_key = join_content_type_with_vnd(content_type, vnd)
        try:
            return self._representations[type_][repr_key]
        except KeyError:
            raise UnknownRepresentation('%s: %s' % (
                            type_, repr_key))

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
