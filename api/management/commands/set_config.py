from django.core.management.base import BaseCommand
from ...models import Config

class Command(BaseCommand):

    def add_arguments(self, parser):
        parser.add_argument('infos', nargs='+', type=str)

    def handle(self, *args, **kwargs):
        infos = kwargs['infos']
        for i in range(len(infos[::2])):
            config, is_created = Config.objects.get_or_create(key=infos[i], defaults={'key': infos[i], 'value': infos[i+1]})
            if not is_created:
                config.value = infos[i+1]
                config.save()
        print('Операция выполнена')

