from django.http import HttpResponse
from django.core.exceptions import PermissionDenied
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings
import telebot

tbot = telebot.TeleBot(settings.TELEGRAM_BOT_API_KEY)
# For free PythonAnywhere accounts
# tbot = telebot.TeleBot(TOKEN, threaded=False)

@csrf_exempt
def bot(request):

    if request.META['CONTENT_TYPE'] == 'application/json':
        
        json_data = request.body.decode('utf-8')
        update = telebot.types.Update.de_json(json_data)
        tbot.process_new_updates([update])

        return HttpResponse("")

    else:
        raise PermissionDenied


@tbot.message_handler(content_types=["text"])
def get_okn(message):
    tbot.send_message(message.chat.id, "Hello, bot!")