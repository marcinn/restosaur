from .forms import modelform_factory, model_to_dict


class Representation(object):
    links = {}

    def __init__(self, context):
        self.context = context

    def to_dict(self, obj):
        data = {}
        data.update(obj)
        data.update({
            '_links': self.links,
            })
        return data


class ModelRepresentation(Representation):
    model = None
    form = None
    fields = '__all__'

    def get_form(self):
        if self.form:
            return self.form
        return modelform_factory(self.model, fields=self.fields)

    def to_dict(self, obj):
        return model_to_dict(obj)

