from django.http import HttpResponse
from django.core.exceptions import PermissionDenied
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings
from .models import Category, Config, Product, ProductCreationCache, ProductSize, ProductSizeCached, UserInfo
from telebot import TeleBot
from telebot import types
from uuid import uuid4
import math

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


def get_menu_markup(user_info_obj: UserInfo):
    if not user_info_obj.is_admin_interface:
        count = 0
        lst = [[types.InlineKeyboardButton('Категория', callback_data='category')]]
        if (user_info_obj.category is not None) and user_info_obj.category.is_size:
            lst[0].append(types.InlineKeyboardButton('Размер', callback_data='size'))
            if user_info_obj.size is not None:
                count = ProductSize.objects.filter(size=user_info_obj.size, product__category=user_info_obj.category).count()
        elif (user_info_obj.category is not None) and not user_info_obj.category.is_size:
            count = Product.objects.filter(category=user_info_obj.category).count()

        markup = types.InlineKeyboardMarkup(keyboard=lst)
        markup.add(types.InlineKeyboardButton(
            f'Товары ( Нашлось {count} )' if count > 0 else 'Товары', callback_data='products'))
        markup.add(types.InlineKeyboardButton(
            'Связаться с продавцом', callback_data='manager'))
    else:
        products_on_page = Config.objects.get(key='products_on_page').value
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton('Добавить/изменить товар', callback_data='category'))
        markup.add(types.InlineKeyboardButton('Username менеджера', callback_data='change_manager'))
        markup.add(types.InlineKeyboardButton('Приветствие при /start', callback_data='change_greetings'))
        markup.add(types.InlineKeyboardButton(f'Товаров на страницу {products_on_page}', callback_data='change_products_on_page'))
        markup.add(types.InlineKeyboardButton('Список администраторов', callback_data='admins'))
    
    if user_info_obj.is_admin:
        markup.add(types.InlineKeyboardButton('Сменить интерфейс', callback_data='change_interface'))
    return markup

def get_menu_title(user_info_obj: UserInfo):
    if not user_info_obj.is_admin_interface:
        category = user_info_obj.category
        cat = category.title if category else 'Не выбрана'
        size = user_info_obj.size if user_info_obj.size else 'Не выбран'
        string = f'<b>Меню</b>\n\nКатегория: <b>{cat}</b>'
        if category and category.is_size:
            string += f'\nРазмер: <b>{size}</b>'
        return string
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
    if obj.is_admin_interface:
        string = f"""
        <b>{product.title}</b>
        
    Размеры <b>{', '.join(available_sizes)}</b>
    Категория <b>{product.category.title}</b>

    Цена <b>{int(product.price)} ₽</b>
        """
    else:
        string = f"""
        <b>{product.title}</b>
        
    Размеры <b>{', '.join(available_sizes)}</b>

    Цена <b>{int(product.price)} ₽</b>
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

def get_cancel_to_markup(callback_data, title='Отмена'):
    return types.InlineKeyboardMarkup(keyboard=[[types.InlineKeyboardButton(title, callback_data=callback_data)]])

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
       

def verify_category(message: types.Message, call_message: types.Message, obj_id, category_id=None):
    call_id = call_message.id
    chat_id = message.chat.id
    text = message.text
    obj = UserInfo.objects.get(pk=obj_id)
    bot.delete_message(chat_id, message.id)
    if category_id:
        Category.objects.filter(pk=category_id).update(title=text)
    else:
        Category.objects.create(title=text)
    
    msg = get_category_message_obj(obj)
    bot.edit_message_text(msg['text'], chat_id, call_id, parse_mode='html', reply_markup=msg['markup'])

def verify_category_in_options(message: types.Message, call_message: types.Message, category_id):
    call_id = call_message.id
    chat_id = message.chat.id
    text = message.text
    bot.delete_message(chat_id, message.id)
    Category.objects.filter(pk=category_id).update(title=text)
    msg = get_category_options_message(category_id)
    bot.edit_message_text(msg['text'], chat_id, call_id, parse_mode='html', reply_markup=msg['markup'])

def get_category_options_message(category_id):
    category = Category.objects.get(pk=category_id)
    cancel_keyboard = [] + get_cancel_to_markup('category', 'Вернуться').keyboard
    lst = []
    lst.append([types.InlineKeyboardButton(category.title, callback_data=f'edit_opt_category_title:{category_id}')])
    lst.append([types.InlineKeyboardButton('С размерами ✅' if category.is_size else 'Без размеров ❌', callback_data=f'change_opt_category_is_size:{category_id}')])
    markup = types.InlineKeyboardMarkup(keyboard = lst + cancel_keyboard)
    return {'text': '<b>Свойства категории</b>', 'markup': markup}

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
        markup.add(types.InlineKeyboardButton('Вернуться', callback_data='return_to_menu'))
    else:
        text = '<b>Опции</b>\n\n➖ Открыть свойства категории\n\n➖ Открыть список товаров в категории\n\n➖ Добавить товар в категорию ➕\n\n➖ Удалить пустую категорию ❌\n\n➖ Добавить категорию'
        lst = []
        for category in Category.objects.all():
            count = Product.objects.filter(category=category).count()
            if count == 0:
                lst.append([types.InlineKeyboardButton(category.title, callback_data=f'open_category_options:{category.id}'), types.InlineKeyboardButton('❌', callback_data=f'delete_category:{category.id}'), types.InlineKeyboardButton('➕', callback_data=f'create_product:{category.id}')])
            else:
                lst.append([types.InlineKeyboardButton(category.title, callback_data=f'open_category_options:{category.id}'), types.InlineKeyboardButton(str(count), callback_data=f'send_products:{category.id}'), types.InlineKeyboardButton('➕', callback_data=f'create_product:{category.id}')])
        lst = sorted([l for l in lst if '❌' not in l[1].text], key=lambda l: int(l[1].text), reverse=True) + [l for l in lst if '❌' in l[1].text]
        lst.append([types.InlineKeyboardButton('Добавить категорию', callback_data='create_category')])
        lst.append([types.InlineKeyboardButton('Вернуться', callback_data='return_to_menu')])
        markup = types.InlineKeyboardMarkup(keyboard=lst)
    
    return {'text': text, 'markup': markup}

def get_sizes_message_obj(obj: UserInfo, callback_data=None):
    category = obj.category
    markup = types.InlineKeyboardMarkup()
    for size in [l[0] for l in ProductSize.objects.filter(product__category=category).values_list('size').distinct()]:
        markup.add(types.InlineKeyboardButton(size, callback_data=f'set_size:{size}'))
    markup.add(types.InlineKeyboardButton('Вернуться', callback_data=(callback_data if callback_data else 'category')))
    return {'text': '<b>Выберите Размер</b>', 'markup': markup}


def get_category_product_markup(product: Product):
    product_id = product.pk
    keyboard = []
    start = []
    end = []
    for category in Category.objects.exclude(pk=product.category.pk):
        cat_button = types.InlineKeyboardButton(category.title, callback_data=f'set_product_category:{product_id}  category_id:{category.pk}')
        if Product.objects.filter(category=category).count() == 0:
            del_button = types.InlineKeyboardButton('❌', callback_data=f'del_category_in_product:{category.pk}  product_id:{product_id}')
            end.append([cat_button, del_button])
        else:
            start.append([cat_button])
    keyboard += start + end
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
            bot.send_photo(chat_id, instance.photo_id, get_product_caption(instance, obj), parse_mode='html', reply_markup=get_desc_markup(instance, obj))
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
        Product.objects.filter(pk=product_id).update(photo_id=file_id)
            
        bot.edit_message_text('Фото обновлено', chat_id, replied_message.id, call_id)
        bot.edit_message_caption('', chat_id, call_id, reply_markup=get_photo_refresh_markup(product_id, replied_message.id))
    else:
        try:
            bot.edit_message_text('Некорректный формат файла. Пришлите фото', chat_id, replied_message.id, call_id)
        except:
            pass
        bot.register_next_step_handler(call_message, verify_product_photo, call_message, replied_message, product_id)

def is_valid(product_cache: ProductCreationCache):
    category = product_cache.category
    is_exist = ProductSizeCached.objects.filter(product_cache=product_cache).exists()
    return (product_cache.title is not None) and \
    ((category.is_size and is_exist) or (not category.is_size)) and \
    (product_cache.price is not None) and \
    (product_cache.photo_id is not None)

def get_create_mode_message_obj(pk):
    product_cache = ProductCreationCache.objects.get(pk=pk)
    category = product_cache.category
    keyboard = []
    keyboard.append([types.InlineKeyboardButton('Название ❌' if product_cache.title is None else f'{product_cache.title} ✅', callback_data=f'create_mode_title:{product_cache.pk}')])
    if category.is_size:
        is_exist = ProductSizeCached.objects.filter(product_cache=product_cache).exists()
        keyboard.append([types.InlineKeyboardButton('Размеры ✅' if is_exist else 'Размеры ❌', callback_data=f'create_mode_open_sizes:{product_cache.pk}')])

    keyboard.append([types.InlineKeyboardButton('Цена ❌' if product_cache.price is None else f'{product_cache.price} ₽ ✅', callback_data=f'create_mode_price:{product_cache.pk}')])
    keyboard.append([types.InlineKeyboardButton('Фото ❌' if product_cache.photo_id is None else 'Фото ✅', callback_data=f'create_mode_photo:{product_cache.pk}')])
    keyboard.append([types.InlineKeyboardButton('Описание ❌' if product_cache.description is None else 'Описание ✅', callback_data=f'create_mode_desc:{product_cache.pk}')])             
    if is_valid(product_cache):
        keyboard.append([types.InlineKeyboardButton('Создать товар ✅', callback_data=f'create_from_cache_product:{pk}')])
    keyboard += get_cancel_to_markup('category', 'Вернуться').keyboard
    
    markup = types.InlineKeyboardMarkup(keyboard=keyboard)
    return {'text': f'Режим создания товара в категории\n\n<b>{category.title}</b>', 'markup': markup}

def verify_create_mode_product_title(message: types.Message, call_message: types.Message, pk):
    chat_id = message.chat.id
    text = message.text
    ProductCreationCache.objects.filter(pk=pk).update(title=text)
    bot.delete_message(chat_id, message.id)
    msg = get_create_mode_message_obj(pk)
    bot.edit_message_text(msg['text'], chat_id, call_message.id, parse_mode='html', reply_markup=msg['markup'])

def get_create_mode_sizes_message_obj(pk):
    product_cache = ProductCreationCache.objects.get(pk=pk)
    cancel_keyboard = get_cancel_to_markup(f'create_product:{product_cache.category.pk}', 'Вернуться').keyboard
    lst = []
    for product_size_cached in ProductSizeCached.objects.filter(product_cache_id=pk):
        lst.append([types.InlineKeyboardButton(f'{product_size_cached.size} ❌', callback_data=f'create_mode_rem_size:{product_size_cached.pk}')])
    
    lst.append([types.InlineKeyboardButton('Добавить размер', callback_data=f'create_mode_create_size:{pk}')])
    markup = types.InlineKeyboardMarkup(keyboard=lst+cancel_keyboard)
    return {'text': 'Размеры', 'markup': markup}

def verify_create_mode_product_size(message: types.Message, call_message: types.Message, pk):
    call_id = call_message.id
    chat_id = message.chat.id
    text = message.text
    bot.delete_message(chat_id, message.id)
    cancel_markup = get_cancel_to_markup(f'create_mode_open_sizes:{pk}')
    if len(text) > 5:
        try:
            bot.edit_message_text('Максимальное количество символов для размера: 5', chat_id, call_id, reply_markup=cancel_markup)
        except:
            pass
        bot.register_next_step_handler(call_message, verify_create_mode_product_size, call_message, pk)
    else:
        ProductSizeCached.objects.create(product_cache_id=pk, size=text)
        msg = get_create_mode_sizes_message_obj(pk)
        bot.edit_message_text(msg['text'], chat_id, call_id, parse_mode='html', reply_markup=msg['markup'])

def verify_create_mode_product_price(message: types.Message, call_message: types.Message, pk):
    call_id = call_message.id
    chat_id = message.chat.id
    text = message.text
    bot.delete_message(chat_id, message.id)
    markup = get_cancel_to_markup(f'create_product:{ProductCreationCache.objects.get(pk=pk).category.pk}')
    try:
        ProductCreationCache.objects.filter(pk=pk).update(price=int(text))
        msg = get_create_mode_message_obj(pk)
        bot.edit_message_text(msg['text'], chat_id, call_id, parse_mode='html', reply_markup=msg['markup'])
    except ValueError:
        try:
            bot.edit_message_text('Некорректный ввод', chat_id, call_id, reply_markup=markup)
        except:
            pass
        bot.register_next_step_handler(call_message, verify_create_mode_product_price, call_message, pk)

def verify_create_mode_product_description(message: types.Message, call_message: types.Message, pk):
    call_id = call_message.id
    chat_id = message.chat.id
    text = message.text
    bot.delete_message(chat_id, message.id)
    ProductCreationCache.objects.filter(pk=pk).update(description=text)
    msg = get_create_mode_message_obj(pk)
    bot.edit_message_text(msg['text'], chat_id, call_id, parse_mode='html', reply_markup=msg['markup'])

def verify_create_mode_product_photo(message: types.Message, call_message: types.Message, pk):
    call_id = call_message.id
    chat_id = message.chat.id
    bot.delete_message(chat_id, message.id)
    markup = get_cancel_to_markup(f'create_product:{ProductCreationCache.objects.get(pk=pk).category.pk}')
    if message.content_type == 'photo':
        file_id = message.photo[-1].file_id
        ProductCreationCache.objects.filter(pk=pk).update(photo_id=file_id)
        msg = get_create_mode_message_obj(pk)
        bot.edit_message_text(msg['text'], chat_id, call_id, parse_mode='html', reply_markup=msg['markup'])
    else:
        try:
            bot.edit_message_text('Некорректный формат файла. Пришлите фото', chat_id, call_id, reply_markup=markup)
        except:
            pass
        bot.register_next_step_handler(call_message, verify_create_mode_product_photo, call_message, pk)


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

@bot.callback_query_handler(func=lambda call: True)
def callback_inline(call):
    chat_id = call.message.chat.id
    message_id = call.message.id
    obj, is_created = UserInfo.objects.get_or_create(chat_id=chat_id, defaults={'chat_id': chat_id})
    bot.clear_step_handler_by_chat_id(chat_id)
    if call.data == 'category':
        msg = get_category_message_obj(obj)
        bot.edit_message_text(msg['text'], chat_id=chat_id, message_id=message_id, reply_markup=msg['markup'], parse_mode='html')
    elif 'set_category' in call.data:
        cat = Category.objects.get(pk=int(call.data.split(':')[1]))
        obj.category = cat
        obj.size = None
        obj.save()
        if cat.is_size:
            msg = get_sizes_message_obj(obj)
            bot.edit_message_text(msg['text'], chat_id=chat_id, message_id=message_id, parse_mode='html', reply_markup=msg['markup'])
        else:
            bot.edit_message_text(get_menu_title(obj), chat_id, message_id, parse_mode='html', reply_markup=get_menu_markup(obj))
    elif call.data == 'size':
        if not obj.category:
            bot.send_message(chat_id, 'Сначала выберите категорию')
        else:
            msg = get_sizes_message_obj(obj, 'return_to_menu')
            bot.edit_message_text(msg['text'], chat_id=chat_id, message_id=message_id, parse_mode='html', reply_markup=msg['markup'])
    
    elif 'set_size' in call.data:
        obj.size = call.data.split(':')[1]
        obj.save()

        bot.edit_message_text(get_menu_title(obj), chat_id=chat_id, message_id=message_id, reply_markup=get_menu_markup(obj), parse_mode='html')

    elif call.data == 'products':
        if obj.category and obj.category.is_size:
            query = ProductSize.objects.filter(product__category=obj.category, size=obj.size)
        else:
            query = Product.objects.filter(category=obj.category)
        if not query.exists():
            bot.send_message(chat_id, '<b>Товаров по данному запросу нет</b>', parse_mode='html')
        else:
            send_products(chat_id, obj, 0, query, obj.category.is_size)

    elif call.data == 'manager':
        manager = Config.objects.get(key='manager')
        markup = get_cancel_to_markup('return_to_menu', 'Ок')
        bot.edit_message_text(manager.value, chat_id, message_id, reply_markup=markup)

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
        bot.edit_message_caption(get_product_caption(product, obj), chat_id, message_id, parse_mode='html', reply_markup=get_desc_markup(product, obj))


    elif 'set_list_page' in call.data:
        index = int(call.data.split(':')[1])
        
        if obj.is_admin_interface:
            query = Product.objects.filter(category=obj.category)
        else:
            if obj.category.is_size:
                query = ProductSize.objects.filter(product__category=obj.category, size=obj.size)
            else:
                query = Product.objects.filter(category=obj.category)
        
        send_products(chat_id, obj, index, query, (not obj.is_admin_interface and obj.category.is_size))        

    elif call.data == 'return_to_menu':
        bot.edit_message_text(get_menu_title(obj), chat_id, message_id, parse_mode='html', reply_markup=get_menu_markup(obj))

#### ADMIN

    elif obj.is_admin:
        if 'create_product' in call.data:
            category_id = int(call.data.split(':')[1])
            product_cache, is_created = ProductCreationCache.objects.get_or_create(user=obj, category_id=category_id, defaults={'user': obj, 'category_id': category_id})
            msg = get_create_mode_message_obj(product_cache.pk)
            bot.edit_message_text(msg['text'], chat_id, message_id, parse_mode='html', reply_markup=msg['markup'])
        
        elif 'create_mode_title' in call.data:
            product_cache_id = int(call.data.split(':')[1])
            product_cache = ProductCreationCache.objects.get(pk=product_cache_id)
            category_id = product_cache.category.pk
            markup = get_cancel_to_markup(f'create_product:{category_id}')
            bot.edit_message_text(f'Введите название\n\nТекущее название <b>{product_cache.title}</b>', chat_id, message_id, parse_mode='html', reply_markup=markup)
            bot.register_next_step_handler(call.message, verify_create_mode_product_title, call.message, product_cache_id)
        
        elif 'create_mode_open_sizes' in call.data:
            pk = int(call.data.split(':')[1])
            msg = get_create_mode_sizes_message_obj(pk)
            bot.edit_message_text(msg['text'], chat_id, message_id, parse_mode='html', reply_markup=msg['markup'])

        elif 'create_mode_create_size' in call.data:
            pk = int(call.data.split(':')[1])
            markup = get_cancel_to_markup(f'create_mode_open_sizes:{pk}')
            bot.edit_message_text('Введите размер', chat_id, message_id, reply_markup=markup)
            bot.register_next_step_handler(call.message, verify_create_mode_product_size, call.message, pk)

        elif 'create_mode_rem_size' in call.data:
            product_size_cached_pk = int(call.data.split(':')[1])
            product_size_cached = ProductSizeCached.objects.get(pk=product_size_cached_pk)
            pk = product_size_cached.product_cache.pk
            cancel_keyboard = get_cancel_to_markup(f'create_mode_open_sizes:{pk}').keyboard
            lst = [[types.InlineKeyboardButton('Удалить', callback_data=f'create_mode_perm_rem_size:{product_size_cached_pk}')]]
            markup = types.InlineKeyboardMarkup(keyboard=lst+cancel_keyboard)
            bot.edit_message_text(f'Удалить размер?\n\n<b>{product_size_cached.size}</b>', chat_id, message_id, parse_mode='html', reply_markup=markup)

        elif 'create_mode_perm_rem_size' in call.data:
            pk = int(call.data.split(':')[1])
            product_cache = ProductSizeCached.objects.get(pk=pk).product_cache
            ProductSizeCached.objects.filter(pk=pk).delete()
            msg = get_create_mode_sizes_message_obj(product_cache.pk)
            bot.edit_message_text(msg['text'], chat_id, message_id, parse_mode='html', reply_markup=msg['markup'])

        elif 'create_mode_price' in call.data:
            pk = int(call.data.split(':')[1])
            product_cache = ProductCreationCache.objects.get(pk=pk)
            category_id = product_cache.category.pk
            markup = get_cancel_to_markup(f'create_product:{category_id}')
            bot.edit_message_text(f'Введите цену\n\nТекущая цена <b>{product_cache.price} ₽</b>', chat_id, message_id, parse_mode='html', reply_markup=markup)
            bot.register_next_step_handler(call.message, verify_create_mode_product_price, call.message, pk)

        elif 'create_mode_desc' in call.data:
            pk = int(call.data.split(':')[1])
            product_cache = ProductCreationCache.objects.get(pk=pk)
            category_id = product_cache.category.pk
            markup = get_cancel_to_markup(f'create_product:{category_id}')
            bot.edit_message_text(f'<b>Текущее описание</b>\n\n{product_cache.description}\n\nВведите описание', chat_id, message_id, parse_mode='html', reply_markup=markup)
            bot.register_next_step_handler(call.message, verify_create_mode_product_description, call.message, pk)

        elif 'create_mode_photo' in call.data:
            pk = int(call.data.split(':')[1])
            product_cache = ProductCreationCache.objects.get(pk=pk)
            category_id = product_cache.category.pk
            markup = get_cancel_to_markup(f'create_product:{category_id}')
            photo_markup = types.InlineKeyboardMarkup(keyboard=[[types.InlineKeyboardButton('Скрыть', callback_data='del_message')]])
            if product_cache.photo_id is not None:
                photo_message = bot.send_photo(chat_id, product_cache.photo_id, '<b>Текущее фото</b>', parse_mode='html', reply_markup=photo_markup)                
            
            bot.edit_message_text('Пришлите фото', chat_id, message_id, reply_markup=markup)
            bot.register_next_step_handler(call.message, verify_create_mode_product_photo, call.message, pk)

        elif 'del_message' in call.data:
            bot.delete_message(chat_id, message_id)

        elif 'create_from_cache_product' in call.data:
            pk = int(call.data.split(':')[1])
            product_cache = ProductCreationCache.objects.get(pk=pk)
            product = Product(title=product_cache.title, description=product_cache.description, category=product_cache.category, price=product_cache.price, photo_id=product_cache.photo_id)
            product.save()
            to_create = [ProductSize(product=product, size=product_cache_size.size) for product_cache_size in ProductSizeCached.objects.filter(product_cache=product_cache)]
            ProductSize.objects.bulk_create(to_create)
            product_cache.delete()
            markup = types.InlineKeyboardMarkup(keyboard=[[types.InlineKeyboardButton('Вернуться в Категории', callback_data='category')]])
            bot.edit_message_text('<b>Товар успешно создан!</b>', chat_id, message_id, parse_mode='html', reply_markup=markup)
                

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
            
            if replied_message_id != 'None':
                bot.delete_message(chat_id, int(replied_message_id))

        elif 'return_admin_to_category' in call.data:
            info = call.data.split('  ')
            product_id = int(info[0].split(':')[1])
            replied_message_id = info[1].split(':')[1]
            
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
            call_message = bot.edit_message_text('<b>Введите название категории</b>', chat_id, message_id, parse_mode='html', reply_markup=markup)
            bot.register_next_step_handler(call_message, verify_category, call_message, obj.pk)

        # elif 'edit_category_title' in call.data:
        #     category_id = int(call.data.split(':')[1])
        #     category = Category.objects.get(pk=category_id)
        #     markup = get_cancel_to_markup('category')
        #     call_message = bot.edit_message_text(f'Введите новое название категории\n\n<b>{category.title}</b>', chat_id, message_id, parse_mode='html', reply_markup=markup)
        #     bot.register_next_step_handler(call_message, verify_category, call_message, obj.pk, category_id)
        
        elif 'edit_opt_category_title' in call.data:
            category_id = int(call.data.split(':')[1])
            category = Category.objects.get(pk=category_id)
            markup = get_cancel_to_markup(f'open_category_options:{category_id}')
            call_message = bot.edit_message_text(f'Введите новое название категории\n\n<b>{category.title}</b>', chat_id, message_id, parse_mode='html', reply_markup=markup)
            bot.register_next_step_handler(call_message, verify_category_in_options, call_message, category_id)

        elif 'change_opt_category_is_size' in call.data:
            category_id = int(call.data.split(':')[1])
            category = Category.objects.get(pk=category_id)
            category.is_size = not category.is_size
            category.save()
            msg = get_category_options_message(category_id)
            bot.edit_message_text(msg['text'], chat_id, message_id, parse_mode='html', reply_markup=msg['markup'])

        elif 'open_category_options' in call.data:
            category_id = int(call.data.split(':')[1])
            msg = get_category_options_message(category_id)
            bot.edit_message_text(msg['text'], chat_id, message_id, parse_mode='html', reply_markup=msg['markup'])
            
        
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

        elif 'send_products' in call.data:
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
            UserInfo.objects.filter(chat_id=admin_chat_id).update(is_admin=False, is_admin_interface=False)
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

            bot.delete_message(chat_id, message_id)

        elif 'change_sizes' in call.data:
            product_id = int(call.data.split(':')[1])
            markup = get_sizes_markup(product_id)
            bot.edit_message_caption('<b>Размеры</b>', chat_id, message_id, parse_mode='html', reply_markup=markup)

        elif 'return_admin_to_sizes' in call.data:
            info = call.data.split('  ')
            product_id = int(info[0].split(':')[1])
            replied_message_id = int(info[1].split(':')[1])
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