class ContentTypeNegotiator(object):
    def __init__(self, available, default):
        self._content_types = available
        self._default = default

        ct_splitted = default.split('/')

        self._default_toplevel = ct_splitted[0]
        self._default_subtype = ct_splitted[1]

    def match(self, content_type):
        if content_type == '*/*':
            return self._default

        toplevel, subtype = content_type.split('/')

        if subtype == '*':
            if self._default_toplevel == toplevel:
                return self._default

            for ct in self._content_types:
                # match best

