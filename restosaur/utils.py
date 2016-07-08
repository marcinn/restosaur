
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
