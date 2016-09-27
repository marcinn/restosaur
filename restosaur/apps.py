from django.apps import AppConfig


class RestosaurAppConfig(AppConfig):
    name = 'restosaur'
    verbose_name = 'Restosaur'

    def ready(self):
        from .settings import AUTODISCOVER_MODULE, AUTODISCOVER
        from . import autodiscover

        if AUTODISCOVER:
            autodiscover(AUTODISCOVER_MODULE)
