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
import hashlib
import logging
import urllib.request
import urllib.parse
from config import (SMS_PROVIDER, SMS_ACCOUNT_SID, SMS_API_KEY, SMS_SENDER,
                    SMS_LOGIN, SMS_PASSWORD)

log = logging.getLogger("sms")


def _normalize_msisdn(phone):
    """Nömrəni LSIM formatına gətirir: 994XXXXXXXXX (+ və boşluqsuz).
    Nümunələr: +994501234567 -> 994501234567; 0501234567 -> 994501234567."""
    digits = ''.join(ch for ch in phone if ch.isdigit())
    if digits.startswith('994'):
        return digits
    if digits.startswith('0'):
        return '994' + digits[1:]
    if len(digits) == 9:  # 501234567
        return '994' + digits
    return digits


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


def _send_lsim(phone, text):
    """LSIM.az QuickSMS API (yerli AZ). İmza: MD5(MD5(parol)+login+text+msisdn+sender)."""
    msisdn = _normalize_msisdn(phone)
    inner = hashlib.md5(SMS_PASSWORD.encode('utf-8')).hexdigest()
    key = hashlib.md5((inner + SMS_LOGIN + text + msisdn + SMS_SENDER).encode('utf-8')).hexdigest()
    params = urllib.parse.urlencode({
        'login': SMS_LOGIN, 'msisdn': msisdn, 'text': text,
        'sender': SMS_SENDER, 'key': key, 'unicode': 'true',
    })
    url = f"https://apps.lsim.az/quicksms/v1/send?{params}"
    try:
        with urllib.request.urlopen(url, timeout=10) as resp:
            data = json.loads(resp.read().decode('utf-8'))
        if data.get('errorCode', -1) == 0:
            return True
        log.error("LSIM SMS xətası: %s", data.get('errorMessage') or data)
        return False
    except Exception as e:
        log.error("LSIM SMS sorğu xətası: %s", e)
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
    if SMS_PROVIDER == 'lsim':
        if not (SMS_LOGIN and SMS_PASSWORD and SMS_SENDER):
            log.error("LSIM konfiqurasiyası natamamdır (SMS_LOGIN/SMS_PASSWORD/SMS_SENDER)")
            return False
        return _send_lsim(phone, text)
    log.error("Naməlum SMS_PROVIDER: %s", SMS_PROVIDER)
    return False


def send_otp(phone, code):
    """Təsdiq kodunu SMS ilə göndərir."""
    return send_sms(phone, f"HeyvanBazar təsdiq kodunuz: {code}")
