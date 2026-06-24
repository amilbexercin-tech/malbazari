# -*- coding: utf-8 -*-
"""Sadə çoxdilli (i18n) dəstək: AZ (defolt), RU, EN.
İstifadə: şablonlarda {{ t('key') }}. Tərcümə yoxdursa AZ-yə, o da yoxdursa açara qayıdır."""

DEFAULT_LANG = 'az'
LANGUAGES = {'az': 'AZ', 'ru': 'RU', 'en': 'EN'}

TRANSLATIONS = {
    # ── Navbar / ümumi ──
    'search_ph':     {'az': 'Axtarış... (inək, qoyun, bal...)', 'ru': 'Поиск... (корова, овца, мёд...)', 'en': 'Search... (cow, sheep, honey...)'},
    'add_listing':   {'az': 'Elan Əlavə Et', 'ru': 'Добавить объявление', 'en': 'Post Listing'},
    'my_profile':    {'az': 'Profilim', 'ru': 'Мой профиль', 'en': 'My Profile'},
    'messages':      {'az': 'Mesajlar', 'ru': 'Сообщения', 'en': 'Messages'},
    'favorites':     {'az': 'Seçilmişlər', 'ru': 'Избранное', 'en': 'Favorites'},
    'admin_panel':   {'az': 'Admin Panel', 'ru': 'Админ-панель', 'en': 'Admin Panel'},
    'logout':        {'az': 'Çıxış', 'ru': 'Выход', 'en': 'Logout'},
    'login':         {'az': 'Giriş', 'ru': 'Вход', 'en': 'Login'},
    'register':      {'az': 'Qeydiyyat', 'ru': 'Регистрация', 'en': 'Register'},
    'all':           {'az': 'Hamısı', 'ru': 'Все', 'en': 'All'},
    'language':      {'az': 'Dil', 'ru': 'Язык', 'en': 'Language'},

    # ── Kateqoriya adları ──
    'cat_mal-qara':  {'az': 'Mal-Qara', 'ru': 'Скот', 'en': 'Cattle'},
    'cat_qusculuq':  {'az': 'Quşçuluq', 'ru': 'Птицеводство', 'en': 'Poultry'},
    'cat_aricilik':  {'az': 'Arıçılıq', 'ru': 'Пчеловодство', 'en': 'Beekeeping'},

    # ── Hero ──
    'hero_badge':    {'az': '🇦🇿 Azərbaycanın №1 Heyvan Bazarı', 'ru': '🇦🇿 Маркетплейс животных №1 в Азербайджане', 'en': "🇦🇿 Azerbaijan's #1 Animal Marketplace"},
    'hero_title_1':  {'az': 'Mal, Quş, Arı', 'ru': 'Скот, Птица, Пчёлы', 'en': 'Cattle, Poultry, Bees'},
    'hero_title_2':  {'az': 'Alın & Satın', 'ru': 'Купить и Продать', 'en': 'Buy & Sell'},
    'all_categories':{'az': 'Bütün kateqoriyalar', 'ru': 'Все категории', 'en': 'All categories'},
    'search_hint':   {'az': 'İnək, qoyun, bal...', 'ru': 'Корова, овца, мёд...', 'en': 'Cow, sheep, honey...'},
    'search_btn':    {'az': 'Axtar', 'ru': 'Найти', 'en': 'Search'},

    # ── AI axtarış ──
    'ai_search_title':{'az': 'AI Axtarış', 'ru': 'AI Поиск', 'en': 'AI Search'},
    'ai_search_ph':  {'az': 'məs: Gəncədə 1500 manata qədər südlük inək...', 'ru': 'напр: дойная корова до 1500 манат в Гяндже...', 'en': 'e.g. dairy cow under 1500 AZN in Ganja...'},
    'ai_search_btn': {'az': '✨ AI ilə axtar', 'ru': '✨ Искать с AI', 'en': '✨ Search with AI'},
    'ai_search_btn_short':{'az': 'AI ilə axtar', 'ru': 'Искать с AI', 'en': 'Search with AI'},
    'ai_search_sub': {'az': 'Nə axtardığınızı adi dildə yazın — AI sizin üçün tapsın', 'ru': 'Напишите обычными словами, что ищете — AI найдёт', 'en': 'Describe what you want in plain words — AI finds it'},
    'advanced_filter':{'az': 'Ətraflı filtr', 'ru': 'Подробный фильтр', 'en': 'Advanced filter'},
    'ai_understood': {'az': 'AI nə anladı:', 'ru': 'AI понял:', 'en': 'AI understood:'},
    'ai_fallback_note':{'az': 'Adi axtarış nəticələri göstərilir.', 'ru': 'Показаны результаты обычного поиска.', 'en': 'Showing standard search results.'},
    'ai_no_results': {'az': 'Uyğun elan tapılmadı', 'ru': 'Подходящих объявлений не найдено', 'en': 'No matching listings found'},
    'ai_no_results_sub':{'az': 'Başqa sözlərlə cəhd edin və ya ətraflı filtrdən istifadə edin', 'ru': 'Попробуйте другие слова или подробный фильтр', 'en': 'Try other words or use the advanced filter'},
    'ai_back_home':  {'az': 'Ana səhifəyə qayıt', 'ru': 'На главную', 'en': 'Back to home'},
    'active_listings':{'az': 'aktiv elan', 'ru': 'активных объявлений', 'en': 'active listings'},
    'users':         {'az': 'istifadəçi', 'ru': 'пользователей', 'en': 'users'},
    'stat_active':   {'az': 'Aktiv Elan', 'ru': 'Активные', 'en': 'Active'},
    'stat_users':    {'az': 'İstifadəçi', 'ru': 'Пользователи', 'en': 'Users'},
    'stat_today':    {'az': 'Bu gün', 'ru': 'Сегодня', 'en': 'Today'},

    # ── Bölmələr ──
    'categories':    {'az': 'Kateqoriyalar', 'ru': 'Категории', 'en': 'Categories'},
    'cat_sub':       {'az': 'İstədiyiniz növü seçin', 'ru': 'Выберите нужный вид', 'en': 'Choose your type'},
    'listings_word': {'az': 'elan', 'ru': 'объявл.', 'en': 'listings'},
    'recent':        {'az': 'Son Elanlar', 'ru': 'Последние объявления', 'en': 'Recent Listings'},
    'see_all':       {'az': 'Hamısını gör', 'ru': 'Смотреть все', 'en': 'See all'},
    'no_listings':   {'az': 'Hələ elan yoxdur', 'ru': 'Объявлений пока нет', 'en': 'No listings yet'},
    'no_listings_sub':{'az': 'İlk elanı siz əlavə edin!', 'ru': 'Добавьте первое объявление!', 'en': 'Be the first to post!'},

    # ── Necə işləyir ──
    'how_title':     {'az': 'Necə İşləyir?', 'ru': 'Как это работает?', 'en': 'How It Works?'},
    'how_sub':       {'az': 'Sadə 3 addımda elan verin', 'ru': 'Разместите объявление в 3 шага', 'en': 'Post a listing in 3 simple steps'},
    'step1_title':   {'az': 'Qeydiyyat', 'ru': 'Регистрация', 'en': 'Sign Up'},
    'step1_desc':    {'az': 'Nömrəniz və şifrənizlə pulsuz qeydiyyatdan keçin', 'ru': 'Бесплатно зарегистрируйтесь по номеру и паролю', 'en': 'Register free with your phone and password'},
    'step2_title':   {'az': 'Elan Əlavə Et', 'ru': 'Добавьте объявление', 'en': 'Post a Listing'},
    'step2_desc':    {'az': 'Şəkil yükləyin, qiymət və məlumatları doldurun', 'ru': 'Загрузите фото, укажите цену и данные', 'en': 'Upload photos, fill in price and details'},
    'step3_title':   {'az': 'Alıcıları Gözləyin', 'ru': 'Ждите покупателей', 'en': 'Wait for Buyers'},
    'step3_desc':    {'az': 'Elanınız 30 gün aktiv qalır, alıcılar sizinlə əlaqə saxlayır', 'ru': 'Объявление активно 30 дней, покупатели свяжутся с вами', 'en': 'Your listing stays active 30 days; buyers contact you'},

    # ── Elan kartı ──
    'negotiable':    {'az': 'Razılaşma ilə', 'ru': 'Договорная', 'en': 'Negotiable'},
    'add_to_fav':    {'az': 'Seçilmişlərə əlavə et', 'ru': 'В избранное', 'en': 'Add to favorites'},

    # ── Footer ──
    'footer_about':  {'az': 'Azərbaycanda mal-qara, quşçuluq və arıçılıq məhsullarının alqı-satqısı üçün ən etibarlı platforma.', 'ru': 'Самая надёжная площадка для купли-продажи скота, птицы и продуктов пчеловодства в Азербайджане.', 'en': 'The most trusted platform for buying and selling cattle, poultry and beekeeping products in Azerbaijan.'},
    'services':      {'az': 'Xidmətlər', 'ru': 'Услуги', 'en': 'Services'},
    'contact':       {'az': 'Əlaqə', 'ru': 'Контакты', 'en': 'Contact'},
    'search_word':   {'az': 'Axtarış', 'ru': 'Поиск', 'en': 'Search'},
    'about_us':      {'az': 'Haqqımızda', 'ru': 'О нас', 'en': 'About Us'},
    'rights':        {'az': 'Bütün hüquqlar qorunur', 'ru': 'Все права защищены', 'en': 'All rights reserved'},
    'location':      {'az': 'Bakı, Azərbaycan', 'ru': 'Баку, Азербайджан', 'en': 'Baku, Azerbaijan'},

    # ── Auth (giriş / qeydiyyat) ──
    'welcome':       {'az': 'Xoş Gəldiniz!', 'ru': 'Добро пожаловать!', 'en': 'Welcome!'},
    'login_sub':     {'az': 'Hesabınıza daxil olun', 'ru': 'Войдите в свой аккаунт', 'en': 'Sign in to your account'},
    'phone_label':   {'az': 'Telefon nömrəsi', 'ru': 'Номер телефона', 'en': 'Phone number'},
    'password_label':{'az': 'Şifrə', 'ru': 'Пароль', 'en': 'Password'},
    'password_ph':   {'az': 'Şifrənizi daxil edin', 'ru': 'Введите пароль', 'en': 'Enter your password'},
    'login_btn':     {'az': 'Daxil Ol', 'ru': 'Войти', 'en': 'Sign In'},
    'no_account':    {'az': 'Hesabınız yoxdur?', 'ru': 'Нет аккаунта?', 'en': "Don't have an account?"},
    'register_sub':  {'az': 'Pulsuz hesab yaradın', 'ru': 'Создайте бесплатный аккаунт', 'en': 'Create a free account'},
    'fullname':      {'az': 'Ad Soyad', 'ru': 'Имя Фамилия', 'en': 'Full Name'},
    'fullname_ph':   {'az': 'Adınızı daxil edin', 'ru': 'Введите ваше имя', 'en': 'Enter your name'},
    'password_min_ph':{'az': 'Ən az 6 simvol', 'ru': 'Минимум 6 символов', 'en': 'At least 6 characters'},
    'confirm_label': {'az': 'Şifrəni Təsdiqlə', 'ru': 'Подтвердите пароль', 'en': 'Confirm Password'},
    'confirm_ph':    {'az': 'Şifrəni yenidən daxil edin', 'ru': 'Введите пароль повторно', 'en': 'Re-enter password'},
    'register_btn':  {'az': 'Qeydiyyatdan Keç', 'ru': 'Зарегистрироваться', 'en': 'Sign Up'},
    'have_account':  {'az': 'Artıq hesabınız var?', 'ru': 'Уже есть аккаунт?', 'en': 'Already have an account?'},
}


def normalize_lang(lang):
    return lang if lang in LANGUAGES else DEFAULT_LANG


def t(key, lang=DEFAULT_LANG):
    entry = TRANSLATIONS.get(key)
    if not entry:
        return key
    return entry.get(lang) or entry.get(DEFAULT_LANG) or key
