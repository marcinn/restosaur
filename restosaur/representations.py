

class Representation(object):
    """
    Manage state representation
    """

    def __init__(self):
        decorators = [
                ('reader', 'read'),
                ('updater', 'update'),
                ('creator', 'create'),
                ('remover', 'remove'),
            ]

        def wrapper_registration(method_name):
            def registrator(func=None):
                if func and not callable(func):
                    raise TypeError('You must set valid callable.')
                if not func:
                    return registrator
                setattr(self, method_name, func)
            return registrator

        for decorator_name, method_name in decorators:
            setattr(self, decorator_name, wrapper_registration(method_name))

    def __call__(self, func):
        """
        Backward compatibility wrapper for registering state reader factory
        """
        return self.reader(func)



