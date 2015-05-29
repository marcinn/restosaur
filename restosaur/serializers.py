import json
import datetime
import decimal


__all__ = ['JsonSerializer', 'registry']



class DefaultRestfulEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, datetime.datetime):
            return obj.isoformat()
        elif isinstance(obj, datetime.date):
            return obj.isoformat()
        elif isinstance(obj, datetime.timedelta):
            return (datetime.datetime.min + obj).time().isoformat()
        elif isinstance(obj, decimal.Decimal):
            return float(str(obj))
        else:
            return super(DefaultRestfulEncoder, self).default(obj)


class DateTimeJsonSerializer(object):
    def dumps(self, obj):
        return json.dumps(obj, cls=DefaultRestfulEncoder)

    def loads(self, txt):
        obj = json.loads(txt)
        return obj


class JsonSerializer(DateTimeJsonSerializer):
    pass


class AlreadyRegistered(Exception):
    pass


class SerializersRegistry(object):
    def __init__(self):
        self._serializers = {}

    def _key(self, mimetype):
        return mimetype.lower()

    def __getitem__(self, item):
        return self._serializers[self._key(str(item))]

    def register(self, mimetype, instance):
        key = self._key(mimetype)
        if key in self._serializers:
            raise AlreadyRegistered(key)
        self._serializers[key] = instance

    def mimetypes(self):
        return self._serializers.keys()

    def items(self):
        return self._serializers.items()

    def contains(self, mimetype):
        return self._key(mimetype) in self._serializers


default_serializers = SerializersRegistry()
default_serializers.register('application/json', JsonSerializer())


def register(mimetype, serializer):
    default_serializers.register(mimetype, serializer)


def get(mimetype):
    return default_serializers.get(mimetype)


