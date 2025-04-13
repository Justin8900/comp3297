from django.apps import AppConfig


class UnihavenConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'unihaven'
    def ready(self):
        import unihaven.models
