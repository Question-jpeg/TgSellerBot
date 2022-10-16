from django.core.management.base import BaseCommand
from ...models import UserInfo

class Command(BaseCommand):

    def add_arguments(self, parser):
        parser.add_argument('chat_ids', nargs='+', type=int)

    def handle(self, *args, **kwargs):
        for chat_id in kwargs['chat_ids']:
            obj, is_created = UserInfo.objects.get_or_create(chat_id=chat_id, defaults={'chat_id': chat_id})
            obj.is_admin = True
            obj.save()
        print('Операция выполнена')

