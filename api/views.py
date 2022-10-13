from django.http import HttpResponse
from django.core.exceptions import PermissionDenied
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings
from .models import Category, Product, ProductSize, UserInfo
from telebot import TeleBot
from telebot import types

bot = TeleBot(settings.TELEGRAM_BOT_API_KEY)
# For free PythonAnywhere accounts
# tbot = telebot.TeleBot(TOKEN, threaded=False)

@csrf_exempt
def tbot(request):

    if request.META['CONTENT_TYPE'] == 'application/json':
        
        json_data = request.body.decode('utf-8')
        update = types.Update.de_json(json_data)
        bot.process_new_updates([update])

        return HttpResponse("")

    else:
        raise PermissionDenied


def get_menu_markup(user_info_obj):
    count = False
    if user_info_obj.category and user_info_obj.size:
        count = ProductSize.objects.filter(size=user_info_obj.size, product__category=user_info_obj.category).count()
    

    markup = types.InlineKeyboardMarkup(keyboard=[[types.InlineKeyboardButton(
        'Категория', callback_data='category'), types.InlineKeyboardButton('Размер', callback_data='size')]])
    markup.add(types.InlineKeyboardButton(
        f'Товары ( Нашлось {count} )' if count else 'Товары', callback_data='products'))
    markup.add(types.InlineKeyboardButton(
        'Связаться с продавцом', callback_data='manager'))
    return markup

def get_menu_title(user_info_obj):
    cat = user_info_obj.category.title if user_info_obj.category else 'Не выбрана'
    size = user_info_obj.size if user_info_obj.size else 'Не выбран'
    return f'<b>Меню</b>\n\n<b>Категория:</b> {cat}\n\n<b>Размер:</b> {size}'

@bot.message_handler(commands=['start'])
def get_okn(message):
    chat_id = message.chat.id
    obj, is_created = UserInfo.objects.get_or_create(chat_id=chat_id, defaults={'chat_id': chat_id})
    bot.send_message(chat_id, "Привет! В этом боте ты можешь посмотреть всю актуальную информацию по предлагаемым товарам. Выбери <b>Категорию</b> и <b>Размер</b>. После нажми <b>Товары</b> для получения списка товаров", reply_markup=get_menu_markup(obj), parse_mode='html')

@bot.message_handler(commands=['menu'])
def send_menu(message):
    chat_id = message.chat.id
    obj, is_created = UserInfo.objects.get_or_create(chat_id=chat_id, defaults={'chat_id': chat_id})
    bot.send_message(chat_id, get_menu_title(obj), reply_markup=get_menu_markup(obj), parse_mode='html')

@bot.message_handler()
def send_buttons(message):
    chat_id = message.chat.id
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add(types.KeyboardButton('/menu'))
    bot.send_message(chat_id, '<b>Нажмите на кнопку /menu для активации меню</b>', parse_mode='html', reply_markup=markup)

@bot.callback_query_handler(func=lambda call: True)
def callback_inline(call):
    chat_id = call.message.chat.id
    message_id = call.message.id
    obj, is_created = UserInfo.objects.get_or_create(chat_id=chat_id, defaults={'chat_id': chat_id})
    if call.data == 'category':
        markup = types.InlineKeyboardMarkup()
        for category in Category.objects.all():
            if Product.objects.filter(category=category).exists():
                markup.add(types.InlineKeyboardButton(category.title, callback_data=f'set_category:{category.id}'))
        bot.edit_message_text('<b>Выберите Категорию</b>', chat_id=chat_id, message_id=message_id, reply_markup=markup, parse_mode='html')
    elif 'set_category' in call.data:
        cat = Category.objects.get(pk=int(call.data.split(':')[1]))
        obj.category = cat
        obj.size = None
        obj.save()

        bot.edit_message_text(get_menu_title(obj), chat_id=chat_id, message_id=message_id, reply_markup=get_menu_markup(obj), parse_mode='html')
    elif call.data == 'size':
        if not obj.category:
            bot.send_message(chat_id, 'Сначала выберите категорию')
        else:
            markup = types.InlineKeyboardMarkup()
            for product_size in ProductSize.objects.filter(product__category=obj.category):
                markup.add(types.InlineKeyboardButton(product_size.size, callback_data=f'set_size:{product_size.size}'))
            bot.edit_message_text('<b>Выберите Размер</b>', chat_id=chat_id, message_id=message_id, reply_markup=markup, parse_mode='html')
    elif 'set_size' in call.data:
        obj.size = call.data.split(':')[1]
        obj.save()

        bot.edit_message_text(get_menu_title(obj), chat_id=chat_id, message_id=message_id, reply_markup=get_menu_markup(obj), parse_mode='html')

