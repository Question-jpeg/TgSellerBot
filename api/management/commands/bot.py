from uuid import uuid4
from django.core.management.base import BaseCommand
from django.core.files import File
from django.conf import settings
from ...models import Category, Config, Product, ProductSize, UserInfo
from telebot import TeleBot
from telebot import types
import math
import os

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
        markup.add(types.InlineKeyboardButton('Список администраторов', callback_data='admins'))
    
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
        first_row = []
        first_row.append(types.InlineKeyboardButton('Заголовок', callback_data=f'change_title:{product.pk}'))
        first_row.append(types.InlineKeyboardButton('Категория', callback_data=f'change_category:{product.pk}'))
        second_row = []
        second_row.append(types.InlineKeyboardButton('Размеры', callback_data=f'change_sizes:{product.pk}'))
        second_row.append(types.InlineKeyboardButton('Цена', callback_data=f'change_price:{product.pk}'))
        third_row = []
        third_row.append(types.InlineKeyboardButton('Фото', callback_data=f'change_photo:{product.pk}'))
        if product.description:
            third_row.append(types.InlineKeyboardButton('Описание', callback_data=f'change_desc:{product.pk}'))
        else:
            third_row.append(types.InlineKeyboardButton('Описания нет', callback_data=f'change_desc:{product.pk}'))
        keyboard = []
        keyboard.append(first_row)
        keyboard.append(second_row)
        keyboard.append(third_row)
        keyboard.append([types.InlineKeyboardButton('Удалить товар ❌', callback_data=f'delete_product:{product.pk}')])
        markup.keyboard = keyboard
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

def get_cancel_to_markup(callback_data):
    return types.InlineKeyboardMarkup(keyboard=[[types.InlineKeyboardButton('Отмена', callback_data=callback_data)]])

def verify_course(message: types.Message, call_message: types.Message, obj_id):
    call_id = call_message.id
    text = message.text
    chat_id = message.chat.id
    markup = get_cancel_to_markup('return_to_menu')
    obj = UserInfo.objects.get(pk=obj_id)
    bot.delete_message(chat_id, message.id)
    try:
        Config.objects.filter(key='course').update(value=float(text))
        bot.edit_message_text(get_menu_title(obj), chat_id, call_id, parse_mode='html', reply_markup=get_menu_markup(obj))
    except ValueError:
        try:
            bot.edit_message_text('Некорректный ввод. Повторите попытку', chat_id, call_id, reply_markup=markup)
        except:
            pass
        bot.register_next_step_handler(call_message, verify_course, call_message, obj.pk)

def verify_manager_username(message: types.Message, call_message: types.Message, obj_id):
    call_id = call_message.id
    chat_id = message.chat.id
    text = message.text
    markup = get_cancel_to_markup('return_to_menu')
    obj = UserInfo.objects.get(pk=obj_id)
    
    bot.delete_message(chat_id, message.id)
    if '@' not in text:
        try:
            bot.edit_message_text('Некорректный ввод. Отсутствует @. Повторите попытку', chat_id, call_id, reply_markup=markup)
        except:
            pass
        bot.register_next_step_handler(call_message, verify_manager_username, call_message, obj.pk)
    elif len(text) == 1:
        try:
            bot.edit_message_text('Некорректный ввод. Повторите попытку', chat_id, call_id, reply_markup=markup)
        except:
            pass
        bot.register_next_step_handler(call_message, verify_manager_username, call_message, obj.pk)
    else:
        Config.objects.filter(key='manager').update(value=text)
        bot.edit_message_text(get_menu_title(obj), chat_id, call_id, parse_mode='html', reply_markup=get_menu_markup(obj))

def verify_greetings(message: types.Message, call_message: types.Message, obj_id):
    call_id = call_message.id
    chat_id = message.chat.id
    text = message.text
    obj = UserInfo.objects.get(pk=obj_id)
    bot.delete_message(chat_id, message.id)
    Config.objects.filter(key='greetings').update(value=text)
    bot.edit_message_text(get_menu_title(obj), chat_id, call_id, parse_mode='html', reply_markup=get_menu_markup(obj))
       

def verify_category(message: types.Message, call_message: types.Message, obj_id):
    call_id = call_message.id
    chat_id = message.chat.id
    text = message.text
    obj = UserInfo.objects.get(pk=obj_id)
    bot.delete_message(chat_id, message.id)
    Category.objects.create(title=text)
    
    msg = get_category_message_obj(obj)
    bot.edit_message_text(msg['text'], chat_id, call_id, parse_mode='html', reply_markup=msg['markup'])

def verify_products_on_page(message: types.Message, call_message: types.Message, obj_id):
    call_id = call_message.id
    chat_id = message.chat.id
    text = message.text
    markup = get_cancel_to_markup('return_to_menu')
    obj = UserInfo.objects.get(pk=obj_id)
    
    bot.delete_message(chat_id, message.id)
    try:
        if int(text) < 1:
            raise ValueError
        Config.objects.filter(key='products_on_page').update(value=text)
        
        bot.edit_message_text(get_menu_title(obj), chat_id, call_id, parse_mode='html', reply_markup=get_menu_markup(obj))
    except ValueError:
        try:
            bot.edit_message_text('Некорректный ввод', chat_id, call_id, reply_markup=markup)
        except:
            pass
        bot.register_next_step_handler(call_message, verify_products_on_page, call_message, obj.pk)

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

def get_category_product_markup(product: Product):
    product_id = product.pk
    keyboard = []
    for category in Category.objects.exclude(pk=product.category.pk):
        lst = []
        cat_button = types.InlineKeyboardButton(category.title, callback_data=f'set_product_category:{product_id}  category_id:{category.pk}')
        lst.append(cat_button)
        if Product.objects.filter(category=category).count() == 0:
            del_button = types.InlineKeyboardButton('❌', callback_data=f'del_category_in_product:{category.pk}  product_id:{product_id}')
            lst.append(del_button)
        keyboard.append(lst)
    keyboard.append([types.InlineKeyboardButton('Создать категорию', callback_data=f'create_category_in_product:{product_id}')])
    keyboard.append([types.InlineKeyboardButton('Вернуться', callback_data=f'return_admin_to_product:{product_id}  reply:None')])

    return types.InlineKeyboardMarkup(keyboard=keyboard)

def get_admins_markup():
    admins = []
    for admin in UserInfo.objects.filter(is_admin=True):
        username = bot.get_chat(admin.chat_id).username
        admins.append([types.InlineKeyboardButton(f'{username}', callback_data=f'send_username:@{username}'), types.InlineKeyboardButton('❌', callback_data=f'exclude_admin:{admin.chat_id}')])

    admins.append([types.InlineKeyboardButton('Добавить', callback_data='add_admin')])
    admins.append([types.InlineKeyboardButton('Вернуться', callback_data='return_to_menu')])
    markup = types.InlineKeyboardMarkup(keyboard=admins)
    return markup

def send_products(chat_id, obj, page_index, query, product_size=True):
    index = page_index
    count = query.count()
    products_on_page = int(Config.objects.get(key='products_on_page').value)
    start_index = index * products_on_page
    max_index = (index+1) * products_on_page

    query = query[start_index:min(query.count(), max_index)]
    if query.count() > 0:
        for row in query:
            if product_size:
                instance = row.product
            else:
                instance = row
            message = bot.send_message(chat_id, 'Загрузка...')
            with open(instance.photo.path, 'rb') as photo:
                bot.send_photo(chat_id, photo, get_product_caption(instance, obj), parse_mode='html', reply_markup=get_desc_markup(instance, obj))
            bot.delete_message(chat_id, message.id)
        send_paginator_message(chat_id, page_index, count)

def get_cancel_product_inline_markup(product_id, replied_message_id):
    return types.InlineKeyboardMarkup(keyboard=[[types.InlineKeyboardButton('Отмена', callback_data=f'return_admin_to_product:{product_id}  reply:{replied_message_id}')]])

def get_cancel_product_inline_to_category_markup(product_id, replied_message_id):
    return types.InlineKeyboardMarkup(keyboard=[[types.InlineKeyboardButton('Отмена', callback_data=f'return_admin_to_category:{product_id}  reply:{replied_message_id}')]])

def verify_product_title(message: types.Message, call_message: types.Message, replied_message: types.Message, product_id, obj_id):
    call_id = call_message.id
    chat_id = message.chat.id
    text = message.text
    bot.delete_message(chat_id, message.id)
    bot.edit_message_text('Заголовок обновлён', chat_id, replied_message.id, inline_message_id=call_id)
    product = Product.objects.get(pk=product_id)
    product.title = text
    product.save()
    bot.edit_message_caption('', chat_id, call_id, parse_mode='html', reply_markup=get_refresh_markup(product_id, replied_message.id))

def verify_product_category(message: types.Message, call_message: types.Message, replied_message: types.Message, product_id, obj_id):
    call_id = call_message.id
    chat_id = message.chat.id
    text = message.text
    Category.objects.create(title=text)
    bot.edit_message_text('Категория создана', chat_id, replied_message.id, call_id)
    bot.delete_message(chat_id, message.id)
    bot.edit_message_caption('', chat_id, call_id, reply_markup=get_refresh_to_category_markup(product_id, replied_message.id))

def verify_product_size(message: types.Message, call_message: types.Message, replied_message: types.Message, product_id):
    call_id = call_message.id
    chat_id = message.chat.id
    text = message.text
    bot.delete_message(chat_id, message.id)
    if len(text) > 5:
        try:
            bot.edit_message_text('Максимальное количество символов для размера: 5', chat_id, replied_message.id, call_id)
        except:
            pass
        bot.register_next_step_handler(call_message, verify_product_size, call_message, replied_message, product_id)
    else:
        ProductSize.objects.create(product_id=product_id, size=text)
        bot.edit_message_text('Размер добавлен', chat_id, replied_message.id, call_id)
        bot.edit_message_caption('', chat_id, call_id, reply_markup=get_refresh_to_sizes_markup(product_id, replied_message.id))

def verify_product_price(message: types.Message, call_message: types.Message, replied_message: types.Message, product_id):
    call_id = call_message.id
    chat_id = message.chat.id
    text = message.text
    bot.delete_message(chat_id, message.id)
    try:
        Product.objects.filter(pk=product_id).update(price=int(text))
        bot.edit_message_text('Цена обновлена', chat_id, replied_message.id, inline_message_id=call_id)
        bot.edit_message_caption('', chat_id, call_id, reply_markup=get_refresh_markup(product_id, replied_message.id))
    except ValueError:
        try:
            bot.edit_message_text('Некорректный ввод', chat_id, replied_message.id, call_id)
        except:
            pass
        bot.register_next_step_handler(call_message, verify_product_price, call_message, replied_message, product_id)

def verify_product_description(message: types.Message, call_message: types.Message, replied_message: types.Message, product_id):
    call_id = call_message.id
    chat_id = message.chat.id
    text = message.text
    Product.objects.filter(pk=product_id).update(description=text)
    bot.delete_message(chat_id, message.id)
    bot.edit_message_text('Описание обновлено', chat_id, replied_message.id, call_id)
    bot.edit_message_caption('', chat_id, call_id, reply_markup=get_refresh_markup(product_id, replied_message.id))

def verify_product_photo(message: types.Message, call_message: types.Message, replied_message: types.Message, product_id):
    call_id = call_message.id
    chat_id = message.chat.id
    bot.delete_message(chat_id, message.id)
    if message.content_type == 'photo':
        file_id = message.photo[-1].file_id
        file_info = bot.get_file(file_id)
        downloaded_file = bot.download_file(file_info.file_path)
        with open(os.path.join(settings.MEDIA_ROOT, 'products', 'photo_' + file_id + '.png'), 'wb') as new_file:
            new_file.write(downloaded_file)
            os.remove(Product.objects.get(pk=product_id).photo.path)
            Product.objects.filter(pk=product_id).update(photo=File(new_file))
            
        bot.edit_message_text('Фото обновлено', chat_id, replied_message.id, call_id)
        bot.edit_message_caption('', chat_id, call_id, reply_markup=get_photo_refresh_markup(product_id, replied_message.id))
    else:
        try:
            bot.edit_message_text('Некорректный формат файла. Пришлите фото', chat_id, replied_message.id, call_id)
        except:
            pass
        bot.register_next_step_handler(call_message, verify_product_photo, call_message, replied_message, product_id)

    

def get_refresh_markup(product_id, replied_message_id):
    return types.InlineKeyboardMarkup(keyboard=[[types.InlineKeyboardButton('Обновить', callback_data=f'refresh:{product_id}  reply_id:{replied_message_id}')]])

def get_photo_refresh_markup(product_id, replied_message_id):
    return types.InlineKeyboardMarkup(keyboard=[[types.InlineKeyboardButton('Обновить', callback_data=f'ref_photo:{product_id}  reply_id:{replied_message_id}')]])

def get_refresh_to_category_markup(product_id, replied_message_id):
    return types.InlineKeyboardMarkup(keyboard=[[types.InlineKeyboardButton('Обновить', callback_data=f'ref_to_category:{product_id}  reply_id:{replied_message_id}')]])

def get_refresh_to_sizes_markup(product_id, replied_message_id):
    return types.InlineKeyboardMarkup(keyboard=[[types.InlineKeyboardButton('Обновить', callback_data=f'ref_to_sizes:{product_id}  reply_id:{replied_message_id}')]])

def get_sizes_markup(product_id):
    markup = types.InlineKeyboardMarkup()
    for product_size in ProductSize.objects.filter(product_id=product_id):
        markup.add(types.InlineKeyboardButton(f'{product_size.size} ❌', callback_data=f'remove_size:{product_size.pk}'))
    markup.add(types.InlineKeyboardButton('Добавить размер', callback_data=f'add_size:{product_id}'))
    markup.add(types.InlineKeyboardButton('Вернуться', callback_data=f'return_admin_to_product:{product_id}  reply:None'))
    return markup

@bot.message_handler(commands=['start'])
def get_okn(message):
    greetings = Config.objects.get(key='greetings').value
    chat_id = message.chat.id
    obj, is_created = UserInfo.objects.get_or_create(chat_id=chat_id, defaults={'chat_id': chat_id})
    bot.send_message(chat_id, greetings, reply_markup=get_menu_markup(obj), parse_mode='html')

@bot.message_handler(commands=['chat'])
def send_chat_id(message: types.Message):
    chat_id = message.chat.id
    bot.send_message(chat_id, f'{chat_id}')

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

def filter_callback_query(call):
    chat_id = call.message.chat.id
    msg_id = call.message.id
    waiting_id = UserInfo.objects.get(chat_id=chat_id).waiting_id
    return not waiting_id or waiting_id == msg_id

@bot.callback_query_handler(func=filter_callback_query)
def callback_inline(call):
    chat_id = call.message.chat.id
    message_id = call.message.id
    obj, is_created = UserInfo.objects.get_or_create(chat_id=chat_id, defaults={'chat_id': chat_id})
    if call.data == 'category':
        if obj.is_admin_interface:
            bot.clear_step_handler(call.message)
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

    # elif 'show_desc' in call.data:
    #     pk, page = call.data.split('  ')
    #     pk, page = int(pk.split(':')[1]), int(page.split(':')[1])

    #     description = Product.objects.get(pk=pk).description
    #     bot.edit_message_caption(f"""<b>Описание</b>
    #     {description}""", chat_id, message_id, parse_mode='html')
        
    #     markup = types.InlineKeyboardMarkup()
    #     markup.add(types.InlineKeyboardButton('Ок', callback_data=f'hide_desc:{pk}  page:{page}'))
    #     bot.edit_message_reply_markup(chat_id, message_id, reply_markup=markup)
    
    # elif 'hide_desc' in call.data:
    #     pk, page = call.data.split('  ')
    #     pk, page = int(pk.split(':')[1]), int(page.split(':')[1])

    #     product = Product.objects.get(pk=pk)
    #     query = ProductSize.objects.filter(product__category=obj.category, size=obj.size)
    #     bot.edit_message_caption(get_product_caption(product, obj), chat_id, message_id, parse_mode='html')
    #     bot.edit_message_reply_markup(chat_id, message_id, reply_markup=get_paginator_markup(page, query))

    elif 'list_desc' in call.data:
        product_pk = int(call.data.split(':')[1])
        product = Product.objects.get(pk=product_pk)
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton('Ok', callback_data=f'return_to_product:{product_pk}'))
        bot.edit_message_caption(f"""<b>Описание</b>
        {product.description}""", chat_id, message_id, parse_mode='html', reply_markup=markup)

    elif 'return_to_product' in call.data:
        product_id = int(call.data.split(':')[1])
        product = Product.objects.get(pk=product_id)
        bot.clear_step_handler(call.message)
        bot.edit_message_caption(get_product_caption(product, obj), chat_id, message_id, parse_mode='html', reply_markup=get_desc_markup(product, obj))


    elif 'set_list_page' in call.data:
        if obj.is_admin_interface:
            query = Product.objects.filter(category=obj.category)
        else:
            query = ProductSize.objects.filter(size=obj.size, product__category=obj.category)
        index = int(call.data.split(':')[1])
        
        send_products(chat_id, obj, index, query, not obj.is_admin_interface)        

    elif call.data == 'return_to_menu':
        if obj.is_admin_interface:
            bot.clear_step_handler(call.message)
        bot.edit_message_text(get_menu_title(obj), chat_id, message_id, parse_mode='html', reply_markup=get_menu_markup(obj))

#### ADMIN

    elif 'refresh' in call.data:
        info = call.data.split('  ')
        product_id = int(info[0].split(':')[1])
        replied_message_id = info[1].split(':')[1]
        product = Product.objects.get(pk=product_id)
        bot.edit_message_caption(get_product_caption(product, obj), chat_id, message_id, parse_mode='html', reply_markup=get_desc_markup(product, obj))
        bot.delete_message(chat_id, replied_message_id)

    elif 'ref_to_category' in call.data:
        info = call.data.split('  ')
        product_id = int(info[0].split(':')[1])
        replied_message_id = info[1].split(':')[1]
        product = Product.objects.get(pk=product_id)
        bot.edit_message_caption('Выберите категорию', chat_id, message_id, parse_mode='html', reply_markup=get_category_product_markup(product))
        bot.delete_message(chat_id, replied_message_id)

    elif 'ref_to_sizes' in call.data:
        info = call.data.split('  ')
        product_id = int(info[0].split(':')[1])
        replied_message_id = info[1].split(':')[1]
        product = Product.objects.get(pk=product_id)
        bot.edit_message_caption('Размеры', chat_id, message_id, parse_mode='html', reply_markup=get_sizes_markup(product_id))
        bot.delete_message(chat_id, replied_message_id)

    elif 'ref_photo' in call.data:        
        info = call.data.split('  ')
        product_id = int(info[0].split(':')[1])
        replied_message_id = info[1].split(':')[1]
        product = Product.objects.get(pk=product_id)
        with open(product.photo.path, 'rb') as photo:
            bot.edit_message_media(types.InputMediaPhoto(photo, get_product_caption(product, obj), parse_mode='html'), chat_id, message_id, reply_markup=get_desc_markup(product, obj))
        bot.delete_message(chat_id, replied_message_id)

    elif 'return_admin_to_product' in call.data:
        info = call.data.split('  ')
        product_id = int(info[0].split(':')[1])
        replied_message_id = info[1].split(':')[1]
        
        product = Product.objects.get(pk=product_id)
        bot.edit_message_caption(get_product_caption(product, obj), chat_id, message_id, parse_mode='html', reply_markup=get_desc_markup(product, obj))
        
        bot.clear_step_handler(call.message)
        if replied_message_id != 'None':
            bot.delete_message(chat_id, int(replied_message_id))

    elif 'return_admin_to_category' in call.data:
        info = call.data.split('  ')
        product_id = int(info[0].split(':')[1])
        replied_message_id = info[1].split(':')[1]
        
        bot.clear_step_handler(call.message)
        bot.edit_message_caption('Выберите категорию', chat_id, message_id, reply_markup=get_category_product_markup(Product.objects.get(pk=product_id)))
        bot.delete_message(chat_id, replied_message_id)

    elif call.data == 'change_interface':
        obj.is_admin_interface = not obj.is_admin_interface
        obj.save()
        bot.edit_message_text(get_menu_title(obj), chat_id, message_id, parse_mode='html', reply_markup=get_menu_markup(user_info_obj=obj))

    elif call.data == 'change_course':
        markup = get_cancel_to_markup('return_to_menu')
        call_message = bot.edit_message_text('<b>Введите новый курс</b>', chat_id, message_id, parse_mode='html', reply_markup=markup)
        bot.register_next_step_handler(call_message, verify_course, call_message, obj.pk)

    elif call.data == 'change_products_on_page':
        markup = get_cancel_to_markup('return_to_menu')
        call_message = bot.edit_message_text('Введите максимальное количество товаров на страницу', chat_id, message_id, reply_markup=markup)
        bot.register_next_step_handler(call_message, verify_products_on_page, call_message, obj.pk)
    
    elif call.data == 'change_manager':
        markup = get_cancel_to_markup('return_to_menu')
        manager = Config.objects.get(key='manager').value
        call_message = bot.edit_message_text(f'Текущее имя менеджера\n{manager}\n\nВведите имя пользователя с "@"', chat_id, message_id, reply_markup=markup)
        bot.register_next_step_handler(call_message, verify_manager_username, call_message, obj.pk)

    elif call.data == 'change_greetings':
        markup = get_cancel_to_markup('return_to_menu')
        greetings = Config.objects.get(key='greetings').value
        call_message = bot.edit_message_text(f'Текущее приветствие\n\n{greetings}\n\nВведите новое', chat_id, message_id, reply_markup=markup)
        bot.register_next_step_handler(call_message, verify_greetings, call_message, obj.pk)

    elif call.data == 'create_category':
        markup = get_cancel_to_markup('category')
        call_message = bot.edit_message_text('<b>Введите название</b>', chat_id, message_id, parse_mode='html', reply_markup=markup)
        bot.register_next_step_handler(call_message, verify_category, call_message, obj.pk)
    
    elif 'delete_category' in call.data:
        category_id = int(call.data.split(':')[1])
        category = Category.objects.get(pk=category_id)
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton('Удалить', callback_data=f'permanent_del_category:{category_id}'))
        markup.add(types.InlineKeyboardButton('Отмена', callback_data='category'))
        bot.edit_message_text(f'Вы уверены, что хотите удалить категорию?\n\n<b>{category.title}</b>', chat_id, message_id, parse_mode='html', reply_markup=markup)
    
    elif 'permanent_del_category' in call.data:
        category_id = int(call.data.split(':')[1])
        category = Category.objects.get(pk=category_id)
        category.delete()
        msg = get_category_message_obj(obj)
        bot.edit_message_text(msg['text'], chat_id, message_id, parse_mode='html', reply_markup=msg['markup'])

    elif 'products' in call.data:
        category_id = int(call.data.split(':')[1])
        obj.category = Category.objects.get(pk=category_id)
        obj.save()
        query = Product.objects.filter(category_id=category_id)
        send_products(chat_id, obj, 0, query, False)

    elif call.data == 'admins':
        bot.edit_message_text('<b>Администраторы</b>', chat_id, message_id, parse_mode='html', reply_markup=get_admins_markup())
    
    elif 'exclude_admin' in call.data:
        admin_chat_id = call.data.split(':')[1]
        username = bot.get_chat(admin_chat_id).username
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton('Исключить', callback_data=f'permanent_del_admin:{admin_chat_id}'))
        markup.add(types.InlineKeyboardButton('Отмена', callback_data='admins'))
        bot.edit_message_text(f'Вы уверены что хотите исключить администратора?\n\n<b>{username}</b>', chat_id, message_id, parse_mode='html', reply_markup=markup)

    elif 'permanent_del_admin' in call.data:
        admin_chat_id = call.data.split(':')[1]
        UserInfo.objects.filter(chat_id=admin_chat_id).update(is_admin=False)
        Config.objects.filter(key='key').update(value=uuid4())
        bot.edit_message_text('<b>Администраторы</b>', chat_id, message_id, parse_mode='html', reply_markup=get_admins_markup())

    elif 'send_username' in call.data:
        username = call.data.split(':')[1]
        bot.send_message(chat_id, username, reply_markup=get_menu_keyboard_markup())

    elif call.data == 'add_admin':
        message = bot.edit_message_text(f'Новый администратор должен отправить боту данную строку', chat_id, message_id)
        markup = types.InlineKeyboardMarkup(keyboard=[[types.InlineKeyboardButton('Ок', callback_data=f'hide_add_admin:{message.id}')]])
        key = Config.objects.get(key='key').value
        bot.send_message(chat_id, f'/key {key}', reply_markup=markup)

    elif 'hide_add_admin' in call.data:
        msg_id = int(call.data.split(':')[1])
        bot.delete_message(chat_id, msg_id)
        bot.edit_message_text('<b>Администраторы</b>', chat_id, message_id, parse_mode='html', reply_markup=get_admins_markup())
    
    elif 'change_title' in call.data:
        product_id = int(call.data.split(':')[1])
        replied_message = bot.send_message(chat_id, 'Вы собираетесь изменить заголовок', reply_to_message_id=call.message.id)
        markup = get_cancel_product_inline_markup(product_id, replied_message.id)
        call_message = bot.edit_message_caption('<b>Введите новый заголовок</b>', chat_id, message_id, parse_mode='html', reply_markup=markup)
        bot.register_next_step_handler(call_message, verify_product_title, call_message, replied_message, product_id, obj.pk)

    
    elif 'change_category' in call.data:
        product_id = int(call.data.split(':')[1])
        product = Product.objects.get(pk=product_id)
        markup = get_category_product_markup(product)
        bot.edit_message_caption('<b>Выберите категорию</b>', chat_id, message_id, parse_mode='html', reply_markup=markup)

    elif 'del_category_in_product' in call.data:
        info = call.data.split('  ')
        cat_id = int(info[0].split(':')[1])
        product_id = int(info[1].split(':')[1])
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton('Удалить', callback_data=f'perm_del_cat_in_product:{cat_id}  product_id:{product_id}'))
        markup.add(types.InlineKeyboardButton('Отмена', callback_data=f'return_to_category_in_product:{product_id}'))
        bot.edit_message_caption(f'Удалить категорию?\n\n<b>{Category.objects.get(pk=cat_id).title}</b>', chat_id, message_id, parse_mode='html', reply_markup=markup)

    elif 'perm_del_cat_in_product' in call.data:
        info = call.data.split('  ')
        category_id = int(info[0].split(':')[1])
        product_id = int(info[1].split(':')[1])
        product = Product.objects.get(pk=product_id)
        Category.objects.filter(pk=category_id).delete()
        bot.edit_message_caption(get_product_caption(product, obj), chat_id, message_id, parse_mode='html', reply_markup=get_category_product_markup(product))

    elif 'return_to_category_in_product' in call.data:
        product_id = int(call.data.split(':')[1])
        product = Product.objects.get(pk=product_id)
        bot.edit_message_caption('<b>Выберите новую категорию</b>', chat_id, message_id, parse_mode='html', reply_markup=get_category_product_markup(product))

    elif 'create_category_in_product' in call.data:
        product_id = int(call.data.split(':')[1])
        product = Product.objects.get(pk=product_id)
        replied_message = bot.send_message(chat_id, 'Вы собираетесь добавить категорию', reply_to_message_id=message_id)
        markup = get_cancel_product_inline_to_category_markup(product_id, replied_message.id)
        bot.edit_message_caption('Введите название категории', chat_id, message_id, reply_markup=markup)
        bot.register_next_step_handler(call.message, verify_product_category, call.message, replied_message, product_id, obj.pk)

    elif 'set_product_category' in call.data:
        info = call.data.split('  ')
        product_id = int(info[0].split(':')[1])
        category_id = int(info[1].split(':')[1])
        cat = Category.objects.get(pk=category_id)
        product = Product.objects.get(pk=product_id)
        product.category = cat
        product.save()

        bot.edit_message_caption(get_product_caption(product, obj), chat_id, message_id, parse_mode='html', reply_markup=get_desc_markup(product, obj))

    elif 'change_sizes' in call.data:
        product_id = int(call.data.split(':')[1])
        markup = get_sizes_markup(product_id)
        bot.edit_message_caption('<b>Размеры</b>', chat_id, message_id, parse_mode='html', reply_markup=markup)

    elif 'return_admin_to_sizes' in call.data:
        info = call.data.split('  ')
        product_id = int(info[0].split(':')[1])
        replied_message_id = int(info[1].split(':')[1])
        bot.clear_step_handler(call.message)
        bot.delete_message(chat_id, replied_message_id)
        bot.edit_message_caption('<b>Размеры</b>', chat_id, message_id, parse_mode='html', reply_markup=get_sizes_markup(product_id))

    elif 'add_size' in call.data:
        product_id = int(call.data.split(':')[1])
        replied_message = bot.send_message(chat_id, 'Вы собираетесь добавить размер', reply_to_message_id=message_id)
        markup = get_cancel_to_markup(f'return_admin_to_sizes:{product_id}  reply_id:{replied_message.id}')
        bot.edit_message_caption('Внесите размер', chat_id, message_id, reply_markup=markup)
        bot.register_next_step_handler(call.message, verify_product_size, call.message, replied_message, product_id)

    elif 'remove_size' in call.data:
        product_size_id = int(call.data.split(':')[1])
        product_size = ProductSize.objects.get(pk=product_size_id)
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton('Удалить', callback_data=f'perm_del_size:{product_size_id}  product_id:{product_size.product.pk}'))
        markup.add(types.InlineKeyboardButton('Отмена', callback_data=f'return_to_sizes_in_product:{product_size.product.pk}'))
        bot.edit_message_caption(f'Удалить размер?\n\n<b>{product_size.size}</b>', chat_id, message_id, parse_mode='html', reply_markup=markup)

    elif 'perm_del_size' in call.data:
        info = call.data.split('  ')
        product_size_id = int(info[0].split(':')[1])
        product_id = int(info[1].split(':')[1])
        ProductSize.objects.filter(pk=product_size_id).delete()
        bot.edit_message_caption('<b>Размеры</b>', chat_id, message_id, parse_mode='html', reply_markup=get_sizes_markup(product_id))

    elif 'return_to_sizes_in_product' in call.data:
        product_id = int(call.data.split(':')[1])
        bot.edit_message_caption('<b>Размеры</b>', chat_id, message_id, parse_mode='html', reply_markup=get_sizes_markup(product_id))

    elif 'change_price' in call.data:
        product_id = int(call.data.split(':')[1])
        replied_message = bot.send_message(chat_id, 'Вы собираетесь изменить цену', reply_to_message_id=message_id)
        markup = get_cancel_product_inline_markup(product_id, replied_message.id)
        bot.edit_message_caption('<b>Введите цену</b>', chat_id, message_id, parse_mode='html', reply_markup=markup)
        bot.register_next_step_handler(call.message, verify_product_price, call.message, replied_message, product_id)

    elif 'change_photo' in call.data:
        product_id = int(call.data.split(':')[1])
        replied_message = bot.send_message(chat_id, 'Вы собираетесь обновить фото', reply_to_message_id=message_id)
        markup = get_cancel_product_inline_markup(product_id, replied_message.id)
        bot.edit_message_caption('<b>Пришлите фото</b>', chat_id, message_id, parse_mode='html', reply_markup=markup)
        bot.register_next_step_handler(call.message, verify_product_photo, call.message, replied_message, product_id)

    elif 'change_desc' in call.data:
        product_id = int(call.data.split(':')[1])
        product = Product.objects.get(pk=product_id)
        replied_message = bot.send_message(chat_id, 'Вы собираетесь изменить описание', reply_to_message_id=message_id)
        markup = get_cancel_product_inline_markup(product_id, replied_message.id)
        bot.edit_message_caption(f'<b>Текущее описание</b>\n\n{product.description}\n\n<b>Введите новое описание</b>', chat_id, message_id, parse_mode='html', reply_markup=markup)
        bot.register_next_step_handler(call.message, verify_product_description, call.message, replied_message, product_id)
    
    elif 'delete_product' in call.data:
        product_id = int(call.data.split(':')[1])
        product = Product.objects.get(pk=product_id)
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton('Удалить', callback_data=f'perm_del_product:{product_id}'))
        markup.add(types.InlineKeyboardButton('Отмена', callback_data=f'return_to_product:{product_id}'))
        bot.edit_message_caption(f'Удалить товар?\n\n<b>{product.title}</b>', chat_id, message_id, parse_mode='html', reply_markup=markup)

    elif 'perm_del_product' in call.data:
        product_id = int(call.data.split(':')[1])
        Product.objects.filter(pk=product_id).delete()
        bot.delete_message(chat_id, message_id)