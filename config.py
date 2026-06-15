import os
import secrets

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# .env faylından ayarları yüklə (varsa) — açarları kodda deyil, .env-də saxla
try:
    from dotenv import load_dotenv
    load_dotenv(os.path.join(BASE_DIR, '.env'))
except ImportError:
    pass


def _load_secret_key():
    """SECRET_KEY: ətraf mühit dəyişənindən, yoxdursa .secret_key faylından oxu;
    o da yoxdursa təsadüfi açar yaradıb fayla yaz (kodda sabit açar saxlanmır)."""
    env = os.environ.get('SECRET_KEY')
    if env:
        return env
    key_file = os.path.join(BASE_DIR, '.secret_key')
    if os.path.exists(key_file):
        with open(key_file, 'r', encoding='utf-8') as f:
            saved = f.read().strip()
        if saved:
            return saved
    key = secrets.token_hex(32)
    with open(key_file, 'w', encoding='utf-8') as f:
        f.write(key)
    return key


SECRET_KEY = _load_secret_key()

# Debug rejimi defolt olaraq SÖNDÜRÜLÜB. Yayımda toxunma.
# Lokal inkişaf üçün: FLASK_DEBUG=1 təyin et.
DEBUG = os.environ.get('FLASK_DEBUG', '').lower() in ('1', 'true', 'yes', 'on')

# İlk admin hesabı (yalnız boş bazanı doldurmaq üçün toxum dəyəri).
# Yayımda ADMIN_PHONE / ADMIN_PASSWORD ətraf mühit dəyişənləri ilə əvəz et.
ADMIN_PHONE = os.environ.get('ADMIN_PHONE', '@Superlahiye@')
ADMIN_PASSWORD = os.environ.get('ADMIN_PASSWORD', '@A7413695a@')

DATABASE_PATH = os.path.join(BASE_DIR, 'malbazari.db')
UPLOAD_FOLDER = os.path.join(BASE_DIR, 'static', 'uploads')
MAX_CONTENT_LENGTH = 16 * 1024 * 1024

CATEGORIES = {
    'mal-qara': {
        'name': 'Mal-Qara',
        'icon': '🐄',
        'color': '#1a472a',
        'bg': 'linear-gradient(135deg,#1a472a,#2d6a4f)',
        'subcategories': ['İnək','Camış','Öküz','Buğa','Düyə','Buzov','Qoyun','Quzu','Keçi','Çəpiş']
    },
    'qusculuq': {
        'name': 'Quşçuluq',
        'icon': '🐔',
        'color': '#b5451b',
        'bg': 'linear-gradient(135deg,#b5451b,#e07850)',
        'subcategories': ['Toyuq','Xoruz','Cücə','Hinduşka','Ördək','Qaz','Güvərçin']
    },
    'aricilik': {
        'name': 'Arıçılıq',
        'icon': '🐝',
        'color': '#c77800',
        'bg': 'linear-gradient(135deg,#c77800,#f4a522)',
        'subcategories': ['Arı ailəsi','Arı pətəyi','Çiçək balı','Dağ balı','Arı südü','Arı mumu']
    }
}

REGIONS = [
    'Bakı','Abşeron','Gəncə','Sumqayıt','Mingəçevir','Naxçıvan',
    'Lənkəran','Şirvan','Şəki','Yevlax','Bərdə','Ağdam','Füzuli',
    'Cəbrayıl','Zəngilan','Qubadlı','Şuşa','Ağcabədi','Ağdaş',
    'Ağstafa','Ağsu','Astara','Balakən','Beyləqan','Biləsuvar',
    'Cəlilabad','Daşkəsən','Göranboy','Gədəbəy','Goygol','Hacıqabul',
    'İmişli','İsmayıllı','Kürdəmir','Lerik','Masallı','Neftçala',
    'Oğuz','Qax','Qazax','Qəbələ','Qobustan','Quba','Qusar',
    'Saatlı','Sabirabad','Salyan','Şamaxı','Şəmkir','Samux',
    'Siyəzən','Tovuz','Ucar','Xaçmaz','Xızı','Zaqatala','Zərdab'
]

FREE_DAYS = 30
MAX_IMAGES = 5

# Heyvana xas seçimlər
PURPOSES = ['Südlük', 'Ətlik', 'Damazlıq', 'Yumurtalıq', 'Digər']

# Sıralama variantları (açar: göstərilən ad)
SORT_OPTIONS = {
    'new': 'Ən yeni',
    'old': 'Ən köhnə',
    'price_asc': 'Qiymət: ucuzdan bahaya',
    'price_desc': 'Qiymət: bahadan ucuza',
}

# OTP / SMS
# Telefon təsdiqi məcburidirmi? Hələlik SÖNDÜRÜLÜB (real SMS qoşulanda .env-də 1 et).
REQUIRE_PHONE_VERIFICATION = os.environ.get('REQUIRE_PHONE_VERIFICATION', '').lower() in ('1', 'true', 'yes')
OTP_TTL_SECONDS = 300          # kodun etibarlılıq müddəti (5 dəqiqə)
SMS_PROVIDER = os.environ.get('SMS_PROVIDER', 'dev')  # 'dev' = kod ekranda göstərilir, 'twilio' = real
SMS_ACCOUNT_SID = os.environ.get('SMS_ACCOUNT_SID', '')  # Twilio Account SID
SMS_API_KEY = os.environ.get('SMS_API_KEY', '')          # Twilio Auth Token
SMS_SENDER = os.environ.get('SMS_SENDER', '')            # Göndərən nömrə (+1...) və ya ad

SUBCATEGORY_EXAMPLES = {
    # Mal-Qara
    'İnək':      'Nümunə: 2 yaşlı inək, 150 kq, peyvəndli, südlük',
    'Camış':     'Nümunə: 3 yaşlı camış, 280 kq, südlük, savalanlı',
    'Öküz':      'Nümunə: 4 yaşlı öküz, 320 kq, kəsimlik',
    'Buğa':      'Nümunə: 2 yaşlı buğa, 250 kq, damızlıq',
    'Düyə':      'Nümunə: 1.5 yaşlı düyə, 160 kq, gəlincik',
    'Buzov':     'Nümunə: 3 aylıq buzov, 60 kq, erkək',
    'Qoyun':     'Nümunə: 1 yaşlı toğlu, 45 kq, peyvəndli',
    'Quzu':      'Nümunə: 2 aylıq quzu, 18 kq, dişi',
    'Keçi':      'Nümunə: 2 yaşlı keçi, 38 kq, südlük',
    'Çəpiş':     'Nümunə: 3 aylıq çəpiş, 12 kq, erkək',
    # Quşçuluq
    'Toyuq':     'Nümunə: 10 ədəd yumurta cinsli toyuq, 2 kq, 6 aylıq',
    'Xoruz':     'Nümunə: 1 ədəd xoruz, 2.5 kq, 8 aylıq',
    'Cücə':      'Nümunə: 50 ədəd cücə, 1 günlük, broylər cinsi',
    'Hinduşka':  'Nümunə: 5 ədəd hinduşka, 4 kq, dişi',
    'Ördək':     'Nümunə: 8 ədəd ördək, 3 kq, ağ cins',
    'Qaz':       'Nümunə: 6 ədəd ev qazı, 5 kq',
    'Güvərçin':  'Nümunə: 20 cüt güvərçin, 500 qr, poçt cinsi',
    # Arıçılıq
    'Arı ailəsi': 'Nümunə: 5 çərçivəli arı ailəsi, ana arı 2024',
    'Arı pətəyi': 'Nümunə: 10 çərçivəli taxta pətək, yeni',
    'Çiçək balı': 'Nümunə: 5 kq çiçək balı, bu ilin məhsulu',
    'Dağ balı':   'Nümunə: 2 kq dağ balı, Şəki bölgəsi',
    'Arı südü':   'Nümunə: 100 qr arı südü, təzə',
    'Arı mumu':   'Nümunə: 1 kq arı mumu, sarı rəng',
}
