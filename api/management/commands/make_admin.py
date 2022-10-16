from django.core.management.base import BaseCommand
from ...models import UserInfo

class Command(BaseCommand):

    def add_arguments(self, parser):
        parser.add_argument('chat_ids', nargs='+', type=int)

    def handle(self, *args, **kwargs):
        UserInfo.objects.filter(chat_id__in=kwargs['chat_ids']).update(is_admin=True)
        print('Операция выполнена')

