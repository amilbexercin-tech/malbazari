# -*- coding: utf-8 -*-
"""SMS göndərmə — pluggable provayder.

Defolt 'dev' rejimində real SMS GÖNDƏRİLMİR — kod log-a yazılır və interfeysdə
göstərilir (test üçün). Production-da SMS_PROVIDER ətraf mühit dəyişənini real
provayderə ('twilio' və ya Azərbaycan operatoru) dəyişib send_sms-i tamamla.
"""
import logging
from config import SMS_PROVIDER, SMS_API_KEY, SMS_SENDER

log = logging.getLogger("sms")


def send_sms(phone, text):
    """Bir SMS göndərir. Uğur olduqda True qaytarır.
    dev rejimində həqiqi göndərmə yoxdur — sadəcə log-a yazır."""
    if SMS_PROVIDER == 'dev':
        log.warning("[DEV SMS] -> %s : %s", phone, text)
        return True

    if SMS_PROVIDER == 'twilio':
        # Nümunə inteqrasiya (twilio paketi və kredensiallar lazımdır):
        # from twilio.rest import Client
        # client = Client(ACCOUNT_SID, SMS_API_KEY)
        # client.messages.create(to=phone, from_=SMS_SENDER, body=text)
        # return True
        raise NotImplementedError("Twilio inteqrasiyası konfiqurasiya edilməyib")

    # Naməlum provayder
    log.error("Naməlum SMS_PROVIDER: %s", SMS_PROVIDER)
    return False


def send_otp(phone, code):
    """Təsdiq kodunu SMS ilə göndərir."""
    return send_sms(phone, f"MalBazari.biz təsdiq kodunuz: {code}")
