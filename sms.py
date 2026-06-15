# -*- coding: utf-8 -*-
"""SMS göndərmə — pluggable provayder.

- SMS_PROVIDER='dev'    : real göndərmə yoxdur, kod log-a yazılır və interfeysdə göstərilir (test).
- SMS_PROVIDER='twilio' : real SMS (Twilio REST API, stdlib urllib ilə — əlavə paket lazım deyil).

Production üçün ətraf mühit dəyişənləri:
  SMS_PROVIDER=twilio
  SMS_ACCOUNT_SID=ACxxxx…
  SMS_API_KEY=<Twilio Auth Token>
  SMS_SENDER=+1xxxxxxxxxx   (Twilio nömrəsi)
"""
import json
import base64
import logging
import urllib.request
import urllib.parse
from config import SMS_PROVIDER, SMS_ACCOUNT_SID, SMS_API_KEY, SMS_SENDER

log = logging.getLogger("sms")


def _send_twilio(phone, text):
    url = f"https://api.twilio.com/2010-04-01/Accounts/{SMS_ACCOUNT_SID}/Messages.json"
    data = urllib.parse.urlencode({
        'To': phone, 'From': SMS_SENDER, 'Body': text,
    }).encode()
    auth = base64.b64encode(f"{SMS_ACCOUNT_SID}:{SMS_API_KEY}".encode()).decode()
    req = urllib.request.Request(url, data=data, headers={
        'Authorization': f'Basic {auth}',
        'Content-Type': 'application/x-www-form-urlencoded',
    })
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            return resp.status in (200, 201)
    except Exception as e:
        log.error("Twilio SMS xətası: %s", e)
        return False


def send_sms(phone, text):
    """Bir SMS göndərir. Uğur olduqda True qaytarır."""
    if SMS_PROVIDER == 'dev':
        log.warning("[DEV SMS] -> %s : %s", phone, text)
        return True
    if SMS_PROVIDER == 'twilio':
        if not (SMS_ACCOUNT_SID and SMS_API_KEY and SMS_SENDER):
            log.error("Twilio konfiqurasiyası natamamdır (SID/KEY/SENDER)")
            return False
        return _send_twilio(phone, text)
    log.error("Naməlum SMS_PROVIDER: %s", SMS_PROVIDER)
    return False


def send_otp(phone, code):
    """Təsdiq kodunu SMS ilə göndərir."""
    return send_sms(phone, f"MalBazari.biz təsdiq kodunuz: {code}")
