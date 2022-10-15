from django.core.management.base import BaseCommand
from django.conf import settings
from ...models import Category, Config, Product, ProductSize, UserInfo
from telebot import TeleBot
from telebot import types
import math

# Объявление переменной бота
bot = TeleBot(settings.TELEGRAM_BOT_API_KEY, threaded=False)


# Название класса обязательно - "Command"
class Command(BaseCommand):

    help = 'Implemented to Django application telegram bot setup command'

    def handle(self, *args, **kwargs):
        print('Бот получил команду на запуск')
        bot.enable_save_next_step_handlers(delay=2) # Сохранение обработчиков
        bot.load_next_step_handlers()								# Загрузка обработчиков
        bot.infinity_polling()			

def get_menu_markup(user_info_obj: UserInfo):
    count = False
    if user_info_obj.category and user_info_obj.size:
        count = ProductSize.objects.filter(size=user_info_obj.size, product__category=user_info_obj.category).count()

    if not user_info_obj.is_admin_interface:
        markup = types.InlineKeyboardMarkup(keyboard=[[types.InlineKeyboardButton(
            'Категория', callback_data='category'), types.InlineKeyboardButton('Размер', callback_data='size')]])
        markup.add(types.InlineKeyboardButton(
            f'Товары ( Нашлось {count} )' if count else 'Товары', callback_data='products'))
        markup.add(types.InlineKeyboardButton(
            'Связаться с продавцом', callback_data='manager'))
    else:
        course = Config.objects.get(key='course').value
        products_on_page = Config.objects.get(key='products_on_page').value
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton('Добавить/изменить товар', callback_data='category'))
        markup.add(types.InlineKeyboardButton(f'Текущий курс {course}', callback_data='change_course'))
        markup.add(types.InlineKeyboardButton('Username менеджера', callback_data='change_manager'))
        markup.add(types.InlineKeyboardButton('Приветствие при /start', callback_data='change_greetings'))
        markup.add(types.InlineKeyboardButton(f'Товаров на страницу {products_on_page}', callback_data='change_products_on_page'))
        markup.add(types.InlineKeyboardButton('Ключ авторизации', callback_data='get_security_key'))
    
    if user_info_obj.is_admin:
        markup.add(types.InlineKeyboardButton('Сменить интерфейс', callback_data='change_interface'))
    return markup

def get_menu_title(user_info_obj: UserInfo):
    if not user_info_obj.is_admin_interface:
        cat = user_info_obj.category.title if user_info_obj.category else 'Не выбрана'
        size = user_info_obj.size if user_info_obj.size else 'Не выбран'
        return f'<b>Меню</b>\n\nКатегория: <b>{cat}</b>\nРазмер: <b>{size}</b>'
    else:
        return f'<b>Администрирование</b>'

def get_paginator_markup(current_page_index, query):
    count = query.count()
    if count > 1:
        first_row = [types.InlineKeyboardButton(str(n) if n != (current_page_index+1) else ('✅'), callback_data=f'set_page_index:{n-1}') for n in range(1, count+1)]
        arrows = []
        if current_page_index-1 >= 0:
            arrows.append(types.InlineKeyboardButton('⬅', callback_data=f'set_page_index:{current_page_index-1}'))
        if current_page_index+1 != count:
            arrows.append(types.InlineKeyboardButton('➡', callback_data=f'set_page_index:{current_page_index+1}'))

    product_size: ProductSize = query[current_page_index]
    description_button = types.InlineKeyboardButton('Описание Товара', callback_data=f'show_desc:{product_size.product.pk}  page:{current_page_index}')
    if product_size.product.description:
        if count > 1:
            markup = types.InlineKeyboardMarkup(keyboard=[[description_button], first_row, arrows])
        else:
            markup = types.InlineKeyboardMarkup()
            markup.add(description_button)
    else:
        if count > 1:
            markup = types.InlineKeyboardMarkup(keyboard=[first_row, arrows])
        else:
            markup = None


    return markup

def send_paginator_message(chat_id, current_page_index, count):
    count_of_pages = math.ceil(count / int(Config.objects.get(key='products_on_page').value))

    if count_of_pages > 1:
        pages = [types.InlineKeyboardButton(str(index+1) if current_page_index != index else '✅', callback_data=f'set_list_page:{index}') for index in range(count_of_pages)]
    else:
        pages = []
    arrows = []
    if current_page_index > 0:
        arrows.append(types.InlineKeyboardButton('⬅', callback_data=f'set_list_page:{current_page_index-1}'))
    if current_page_index < (count_of_pages-1):
        arrows.append(types.InlineKeyboardButton('➡', callback_data=f'set_list_page:{current_page_index+1}'))
    
    bot.send_message(chat_id, f'Страницы ({current_page_index+1} из {count_of_pages})', reply_markup=types.InlineKeyboardMarkup(keyboard=[pages, arrows]))




def get_desc_markup(product: Product, obj: UserInfo):
    markup = types.InlineKeyboardMarkup()
    if not obj.is_admin_interface:
        if product.description:
            markup.add(types.InlineKeyboardButton('Описание Товара', callback_data=f'list_desc:{product.pk}'))

    else:
        if product.description:
            markup.add(types.InlineKeyboardButton('Изменить Описание', callback_data=f'change_desc:{product.pk}'))
        else:
            markup.add(types.InlineKeyboardButton('Описания нет', callback_data=f'change_desc:{product.pk}'))
        
        # markup.add()
    return markup


def get_product_caption(product: Product, obj: UserInfo):
    available_sizes = [l[0] for l in list(ProductSize.objects.filter(product=product).values_list('size'))]
    multiplier = float(Config.objects.get(key='course').value)
    if obj.is_admin_interface:
        string = f"""
        <b>{product.title}</b>
        
        Размеры <b>{', '.join(available_sizes)}</b>
        Категория <b>{product.category.title}</b>

        Цена <b>{int(product.price * multiplier)} ₽</b>
        {product.price} ¥  Курс {multiplier}
        """
    else:
        string = f"""
        <b>{product.title}</b>
        
        Размеры <b>{', '.join(available_sizes)}</b>

        Цена <b>{int(product.price * multiplier)} ₽</b>
        """
    return string
    

def get_canceling_keyboard_markup():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add(types.KeyboardButton('Отмена'))
    return markup
def get_menu_keyboard_markup():
    menu_markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    menu_markup.add(types.KeyboardButton('/menu'))
    return menu_markup

def verify_course(message: types.Message):
    text = message.text
    chat_id = message.chat.id
    menu_markup = get_menu_keyboard_markup()
    markup = get_canceling_keyboard_markup()
    obj = UserInfo.objects.get(chat_id=chat_id)
    if text == 'Отмена':
        bot.send_message(chat_id, 'Операция отменена', reply_markup=menu_markup)
        bot.send_message(chat_id, get_menu_title(obj), parse_mode='html', reply_markup=get_menu_markup(obj))
        obj.is_waiting = False
        obj.save()
        return
    try:
        float(text)
        course = Config.objects.get(key='course')
        course.value = float(text)
        course.save()
        bot.send_message(chat_id, 'Курс успешно обновлён', reply_markup=menu_markup)
        bot.send_message(chat_id, get_menu_title(obj), parse_mode='html', reply_markup=get_menu_markup(obj))
        obj.is_waiting = False
        obj.save()
    except ValueError:
        call_message = bot.send_message(chat_id, 'Некорректный ввод. Повторите попытку', reply_markup=markup)
        bot.register_next_step_handler(call_message, verify_course)

def verify_manager_username(message: types.Message):
    chat_id = message.chat.id
    text = message.text
    menu_markup = get_menu_keyboard_markup()
    markup = get_canceling_keyboard_markup()
    obj = UserInfo.objects.get(chat_id=chat_id)
    if text == 'Отмена':
        bot.send_message(chat_id, 'Операция отменена', reply_markup=menu_markup)
        bot.send_message(chat_id, get_menu_title(obj), parse_mode='html', reply_markup=get_menu_markup(obj))
        obj.is_waiting = False
        obj.save()
    elif '@' not in text:
        call_message = bot.send_message(chat_id, 'Некорректный ввод. Отсутствует @. Повторите попытку', reply_markup=markup)
        bot.register_next_step_handler(call_message, verify_manager_username)
    elif len(text) == 1:
        call_message = bot.send_message(chat_id, 'Некорректный ввод. Повторите попытку', reply_markup=markup)
        bot.register_next_step_handler(call_message, verify_manager_username)
    else:
        manager = Config.objects.get(key='manager')
        manager.value = text
        manager.save()
        bot.send_message(chat_id, 'Username менеджера обновлено', reply_markup=menu_markup)
        bot.send_message(chat_id, get_menu_title(obj), parse_mode='html', reply_markup=get_menu_markup(obj))
        obj.is_waiting = False
        obj.save()

def verify_greetings(message: types.Message):
    chat_id = message.chat.id
    text = message.text
    menu_markup = get_menu_keyboard_markup()
    obj = UserInfo.objects.get(chat_id=chat_id)
    if text == 'Отмена':
        bot.send_message(chat_id, 'Операция отменена', reply_markup=menu_markup)
        bot.send_message(chat_id, get_menu_title(obj), parse_mode='html', reply_markup=get_menu_markup(obj))
        obj.is_waiting = False
        obj.save()
    else:
        greetings = Config.objects.get(key='greetings')
        greetings.value = text
        greetings.save()
        bot.send_message(chat_id, 'Приветствие успешно обновлено', reply_markup=menu_markup)
        bot.send_message(chat_id, get_menu_title(obj), parse_mode='html', reply_markup=get_menu_markup(obj))
        obj.is_waiting = False
        obj.save()

def verify_category(message: types.Message):
    chat_id = message.chat.id
    text = message.text
    obj = UserInfo.objects.get(chat_id=chat_id)
    menu_markup = get_menu_keyboard_markup()
    if text == 'Отмена':
        obj.is_waiting = False
        obj.save()
        bot.send_message(chat_id, 'Операция отменена', reply_markup=menu_markup)
        
        msg = get_category_message_obj(obj)
        bot.send_message(chat_id, msg['text'], parse_mode='html', reply_markup=msg['markup'])
    else:
        Category.objects.create(title=text)
        obj.is_waiting = False
        obj.save()
        bot.send_message(chat_id, 'Категория создана', reply_markup=menu_markup)
        
        msg = get_category_message_obj(obj)
        bot.send_message(chat_id, msg['text'], parse_mode='html', reply_markup=msg['markup'])

def verify_products_on_page(message: types.Message):
    chat_id = message.chat.id
    text = message.text
    obj = UserInfo.objects.get(chat_id=chat_id)
    markup = get_canceling_keyboard_markup()
    menu_markup = get_menu_keyboard_markup()
    if text == 'Отмена':
        obj.is_waiting = False
        obj.save()
        bot.send_message(chat_id, 'Операция отменена', reply_markup=menu_markup)
        bot.send_message(chat_id, get_menu_title(obj), parse_mode='html', reply_markup=get_menu_markup(obj))
        return
    try:
        int(text)
        products_on_page = Config.objects.get(key='products_on_page')
        products_on_page.value = text
        products_on_page.save()
        obj.is_waiting = False
        obj.save()
        bot.send_message(chat_id, 'Количество товаров на странице успешно обновлено', reply_markup=menu_markup)
        bot.send_message(chat_id, get_menu_title(obj), parse_mode='html', reply_markup=get_menu_markup(obj))
    except ValueError:
        call_message = bot.send_message(chat_id, 'Некорректный ввод', reply_markup=markup)
        bot.register_next_step_handler(call_message, verify_products_on_page)

def get_category_message_obj(obj: UserInfo):
    if not obj.is_admin_interface:
        text = '<b>Выберите Категорию</b>'
        markup = types.InlineKeyboardMarkup()
        for category in Category.objects.filter(pk__in=[l[0] for l in Product.objects.values_list('category').distinct()]):
            markup.add(types.InlineKeyboardButton(category.title, callback_data=f'set_category:{category.id}'))
    else:
        text = '<b>Опции</b>\n\n➖ Добавить товар в категорию (нажмите на категорию)\n\n➖ Открыть список товаров в категории\n\n➖ Удалить пустую категорию ❌\n\n➖ Добавить категорию'
        lst = []
        for category in Category.objects.all():
            count = Product.objects.filter(category=category).count()
            if count == 0:
                lst.append([types.InlineKeyboardButton(category.title, callback_data=f'create_product:{category.id}'), types.InlineKeyboardButton('❌', callback_data=f'delete_category:{category.id}')])
            else:
                lst.append([types.InlineKeyboardButton(category.title, callback_data=f'create_product:{category.id}'), types.InlineKeyboardButton(str(count), callback_data=f'products:{category.id}')])
        lst = sorted([l for l in lst if '❌' not in l[1].text], key=lambda l: int(l[1].text), reverse=True) + [l for l in lst if '❌' in l[1].text]
        lst.append([types.InlineKeyboardButton('Добавить категорию', callback_data='create_category')])
        lst.append([types.InlineKeyboardButton('Вернуться', callback_data='return_to_menu')])
        markup = types.InlineKeyboardMarkup(keyboard=lst)
    
    return {'text': text, 'markup': markup}

def send_products(chat_id, obj, page_index, query, product_size=True):
    index = page_index
    products_on_page = int(Config.objects.get(key='products_on_page').value)
    start_index = index * products_on_page
    max_index = (index+1) * products_on_page

    for row in query[start_index:min(query.count(), max_index)]:
        if product_size:
            instance = row.product
        else:
            instance = row
        message = bot.send_message(chat_id, 'Загрузка...')
        with open(instance.photo.path, 'rb') as photo:
            bot.send_photo(chat_id, photo, get_product_caption(instance, obj), parse_mode='html', reply_markup=get_desc_markup(instance, obj))
        bot.delete_message(chat_id, message.id)

@bot.message_handler(commands=['start'])
def get_okn(message):
    greetings = Config.objects.get(key='greetings').value
    chat_id = message.chat.id
    obj, is_created = UserInfo.objects.get_or_create(chat_id=chat_id, defaults={'chat_id': chat_id})
    bot.send_message(chat_id, greetings, reply_markup=get_menu_markup(obj), parse_mode='html')

@bot.message_handler(commands=['menu'])
def send_menu(message):
    chat_id = message.chat.id
    obj, is_created = UserInfo.objects.get_or_create(chat_id=chat_id, defaults={'chat_id': chat_id})
    bot.send_message(chat_id, get_menu_title(obj), reply_markup=get_menu_markup(obj), parse_mode='html')

@bot.message_handler(commands=['key'])
def verify(message: types.Message):
    chat_id = message.chat.id
    obj, is_created = UserInfo.objects.get_or_create(chat_id=chat_id, defaults={'chat_id': chat_id})
    key = Config.objects.get(key='key').value
    if message.text.split(' ')[1] == key:
        obj.is_admin = True
        obj.save()
        bot.send_message(chat_id, 'Вы авторизованы. Добро пожаловать, админ.')
    else:
        bot.send_message(chat_id, 'Неверный ключ авторизации')

@bot.message_handler()
def send_buttons(message):
    chat_id = message.chat.id
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add(types.KeyboardButton('/menu'))
    bot.send_message(chat_id, '<b>Нажмите на кнопку /menu для активации меню</b>', parse_mode='html', reply_markup=markup)

@bot.callback_query_handler(func=lambda call: not UserInfo.objects.filter(chat_id=call.message.chat.id).exists() or not UserInfo.objects.get(chat_id=call.message.chat.id).is_waiting)
def callback_inline(call):
    chat_id = call.message.chat.id
    message_id = call.message.id
    obj, is_created = UserInfo.objects.get_or_create(chat_id=chat_id, defaults={'chat_id': chat_id})
    if call.data == 'category':
        msg = get_category_message_obj(obj)
        bot.edit_message_text(msg['text'], chat_id=chat_id, message_id=message_id, reply_markup=msg['markup'], parse_mode='html')
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
            for size in [l[0] for l in ProductSize.objects.filter(product__category=obj.category).values_list('size').distinct()]:
                markup.add(types.InlineKeyboardButton(size, callback_data=f'set_size:{size}'))
            bot.edit_message_text('<b>Выберите Размер</b>', chat_id=chat_id, message_id=message_id, reply_markup=markup, parse_mode='html')
    
    elif 'set_size' in call.data:
        obj.size = call.data.split(':')[1]
        obj.save()

        bot.edit_message_text(get_menu_title(obj), chat_id=chat_id, message_id=message_id, reply_markup=get_menu_markup(obj), parse_mode='html')

    elif call.data == 'products':
        query = ProductSize.objects.filter(product__category=obj.category, size=obj.size)
        if not query.exists():
            bot.send_message(chat_id, '<b>Товаров по данному запросу нет</b>', parse_mode='html')
        # elif not product_size and obj.is_admin_interface:
        #     markup = types.InlineKeyboardMarkup()
        #     markup.add(types.InlineKeyboardButton('Добавить', callback_data='create_product'))
        #     bot.send_message(chat_id, 'Товаров в данной категории нет', reply_markup=markup)
        else:
            send_products(chat_id, obj, 0, query)
            send_paginator_message(chat_id, 0, query.count())
            # with open(product_size.product.photo.path, 'rb') as photo:                
            #     bot.send_photo(chat_id, photo, get_product_caption(product_size.product), reply_markup=get_paginator_markup(0, query), parse_mode='html')
    
    elif 'set_page_index' in call.data:
        page = int(call.data.split(':')[1])
        query = ProductSize.objects.filter(product__category=obj.category, size=obj.size)
        product_size = query[page]
        bot.edit_message_caption('Загрузка...', chat_id, message_id)
        with open(product_size.product.photo.path, 'rb') as photo:
            bot.edit_message_media(types.InputMediaPhoto(photo), chat_id, message_id)
        bot.edit_message_caption(get_product_caption(product_size.product, obj), chat_id, message_id, parse_mode='html', reply_markup=get_paginator_markup(page, query))

    elif call.data == 'manager':
        manager = Config.objects.get(key='manager')
        bot.send_message(chat_id, manager.value)

    elif 'show_desc' in call.data:
        pk, page = call.data.split('  ')
        pk, page = int(pk.split(':')[1]), int(page.split(':')[1])

        description = Product.objects.get(pk=pk).description
        bot.edit_message_caption(f"""<b>Описание</b>
        {description}""", chat_id, message_id, parse_mode='html')
        
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton('Ок', callback_data=f'hide_desc:{pk}  page:{page}'))
        bot.edit_message_reply_markup(chat_id, message_id, reply_markup=markup)
    
    elif 'hide_desc' in call.data:
        pk, page = call.data.split('  ')
        pk, page = int(pk.split(':')[1]), int(page.split(':')[1])

        product = Product.objects.get(pk=pk)
        query = ProductSize.objects.filter(product__category=obj.category, size=obj.size)
        bot.edit_message_caption(get_product_caption(product, obj), chat_id, message_id, parse_mode='html')
        bot.edit_message_reply_markup(chat_id, message_id, reply_markup=get_paginator_markup(page, query))

    elif 'list_desc' in call.data:
        product_pk = int(call.data.split(':')[1])
        product = Product.objects.get(pk=product_pk)
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton('Ok', callback_data=f'fold_desc:{product_pk}'))
        bot.edit_message_caption(f"""<b>Описание</b>
        {product.description}""", chat_id, message_id, parse_mode='html', reply_markup=markup)
    
    elif 'fold_desc' in call.data:
        product_pk = int(call.data.split(':')[1])
        product = Product.objects.get(pk=product_pk)
        bot.edit_message_caption(get_product_caption(product, obj), chat_id, message_id, parse_mode='html', reply_markup=get_desc_markup(product, obj))

    elif 'set_list_page' in call.data:
        query = ProductSize.objects.filter(size=obj.size, product__category=obj.category)
        index = int(call.data.split(':')[1])
        
        send_products(chat_id, obj, index, query)        
        send_paginator_message(chat_id, index, query.count())

    elif call.data == 'return_to_menu':
        bot.edit_message_text(get_menu_title(obj), chat_id, message_id, parse_mode='html', reply_markup=get_menu_markup(obj))

#### ADMIN

    elif call.data == 'change_interface':
        obj.is_admin_interface = not obj.is_admin_interface
        obj.save()
        bot.edit_message_text(get_menu_title(obj), chat_id, message_id, parse_mode='html', reply_markup=get_menu_markup(user_info_obj=obj))

    elif call.data == 'change_course':
        markup = get_canceling_keyboard_markup()
        obj.is_waiting = True
        obj.save()
        call_message = bot.send_message(chat_id, 'Введите новый курс', reply_markup=markup)
        bot.register_next_step_handler(call_message, verify_course)

    elif call.data == 'change_products_on_page':
        markup = get_canceling_keyboard_markup()
        obj.is_waiting = True
        obj.save()
        call_message = bot.send_message(chat_id, 'Введите максимальное количество товаров на страницу', reply_markup=markup)
        bot.register_next_step_handler(call_message, verify_products_on_page)
    
    elif call.data == 'change_manager':
        markup = get_canceling_keyboard_markup()
        manager = Config.objects.get(key='manager').value
        obj.is_waiting = True
        obj.save()
        call_message = bot.send_message(chat_id, f'Текущее имя менеджера\n{manager}\n\nВведите имя пользователя с "@"', reply_markup=markup)
        bot.register_next_step_handler(call_message, verify_manager_username)

    elif call.data == 'change_greetings':
        markup = get_canceling_keyboard_markup()
        greetings = Config.objects.get(key='greetings').value
        obj.is_waiting = True
        obj.save()
        call_message = bot.send_message(chat_id, f'Текущее приветствие\n\n{greetings}', parse_mode='html', reply_markup=markup)
        bot.register_next_step_handler(call_message, verify_greetings)

    elif call.data == 'get_security_key':
        menu_markup = get_menu_keyboard_markup()
        key = Config.objects.get(key='key').value
        bot.send_message(chat_id, f'Ключ авторизации:\n\n{key}', reply_markup=menu_markup)

    elif call.data == 'create_category':
        markup = get_canceling_keyboard_markup()
        obj.is_waiting = True
        obj.save()
        call_message = bot.send_message(chat_id, 'Введите название', reply_markup=markup)
        bot.register_next_step_handler(call_message, verify_category)
    
    elif 'delete_category' in call.data:
        category_id = int(call.data.split(':')[1])
        category = Category.objects.get(pk=category_id)
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton('Удалить', callback_data=f'permanent_del_category:{category_id}'))
        markup.add(types.InlineKeyboardButton('Отмена', callback_data='cancel_category_deletion'))
        bot.edit_message_text(f'Вы уверены, что хотите удалить категорию?\n\n<b>{category.title}</b>', chat_id, message_id, parse_mode='html', reply_markup=markup)
    
    elif 'permanent_del_category' in call.data:
        category_id = int(call.data.split(':')[1])
        category = Category.objects.get(pk=category_id)
        category.delete()
        msg = get_category_message_obj(obj)
        bot.edit_message_text(msg['text'], chat_id, message_id, parse_mode='html', reply_markup=msg['markup'])
    
    elif call.data == 'cancel_category_deletion':
        msg = get_category_message_obj(obj)
        bot.edit_message_text(msg['text'], chat_id, message_id, parse_mode='html', reply_markup=msg['markup'])

    elif 'products' in call.data:
        category_id = int(call.data.split(':')[1])
        query = Product.objects.filter(category_id=category_id)
        send_products(chat_id, obj, 0, query, False)
        send_paginator_message(chat_id, 0, query.count())
