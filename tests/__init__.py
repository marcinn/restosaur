from django.conf import settings

settings.configure(**{
    'ALLOWED_HOSTS': ['testserver'],
    'DEBUG': False,
    })

