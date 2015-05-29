

def model_to_dict(obj, context):
    """
    Convert django model instance to dict
    """

    data = {}

    for field in obj._meta.fields:
        field_name = field.column if field.rel else field.name
        data[field.column] = getattr(obj, field_name)

    return data

