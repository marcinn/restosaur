from . import contentnegotiation


def model_to_dict(obj, context):
    """
    Convert django model instance to dict
    """

    data = {}

    for field in obj._meta.fields:
        field_name = field.column if field.rel else field.name
        data[field.column] = getattr(obj, field_name)

    return data


class Collection(object):
    def __init__(
            self, context, iterable, key=None, totalcount=None,
            totalcount_key=None):

        self.totalcount = totalcount or len(iterable)
        self.iterable = iterable
        self.totalcount_key = totalcount_key or 'totalCount'
        self.key = key or 'items'


def join_content_type_with_vnd(content_type, vnd):
    if not vnd:
        return content_type

    x, y = content_type.split('/')
    return '%s/%s+%s' % (x, vnd, y)


def autodiscover(module_name='restapi'):
    from django.conf import settings

    try:
        from django.utils.module_loading import autodiscover_modules
    except ImportError:
        from django.utils.importlib import import_module
        from django.utils.module_loading import module_has_submodule
        autodiscover_modules = None

    if autodiscover_modules:
        autodiscover_modules(module_name)
    else:
        for app in settings.INSTALLED_APPS:
            mod = import_module(app)
            try:
                import_module('%s.%s' % (app, module_name))
            except:
                if module_has_submodule(mod, module_name):
                    raise


def split_mediatype(mt):
    """
    Split media type into (content_type, vnd, params) tuple

    Function converts `type/[tree.]subtype[+suffix][;params]`
    into generic mediatype together with subtype without suffix.
    Extra parameteres are returned as third element of the tuple.
    """

    type_, subtype, args = contentnegotiation.parse_media_type(mt)
    suffix = subtype.split('+')[-1] if '+' in subtype else None

    if suffix and suffix not in (
            'json', 'zip', 'ber', 'der', 'fastinfoset', 'wbxml'):
        raise ValueError('Suffix "%s" is not supported (see: RFC6839)')

    ct = '%s/%s' % (type_, suffix or subtype)
    vnd = subtype.split('+')[0] if suffix else None
    return ct, vnd, args


def generic_mediatype(mt):
    return split_mediatype(mt)[0]
