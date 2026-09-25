from __future__ import annotations
import asyncio
import os
import logging
from typing import Dict
from twilio.base.exceptions import TwilioRestException
from twilio.rest import Client

# Configuration du logger pour le suivi des erreurs en prod
logger = logging.getLogger(__name__)

def _get_twilio_credentials() -> tuple[str, str, str]:
    """Récupère les identifiants depuis les variables d'environnement."""
    account_sid = os.getenv("TWILIO_ACCOUNT_SID", "").strip()
    auth_token = os.getenv("TWILIO_AUTH_TOKEN", "").strip()
    from_number = os.getenv("TWILIO_PHONE_NUMBER", "").strip()
    
    if not all([account_sid, auth_token, from_number]):
        raise RuntimeError("Variables Twilio manquantes dans le .env")
    return account_sid, auth_token, from_number

async def send_sms(to: str, body: str, from_number: str | None = None) -> str:
    """Envoie un SMS via Twilio. Remplace 'whatsapp:' si présent par précaution."""
    account_sid, auth_token, default_from = _get_twilio_credentials()
    sender = from_number if from_number else default_from
    
    # Nettoyage systématique des préfixes
    clean_to = to.replace("whatsapp:", "").strip()
    clean_from = sender.replace("whatsapp:", "").strip()

    def _send_sync() -> str:
        client = Client(account_sid, auth_token)
        return client.messages.create(from_=clean_from, to=clean_to, body=body).sid

    try:
        sid = await asyncio.to_thread(_send_sync)
        logger.info(f"SMS envoyé avec succès au {clean_to}")
        return sid
    except TwilioRestException as e:
        logger.error(f"Erreur Twilio SMS: {e.msg}")
        raise RuntimeError(f"Échec envoi SMS: {e.msg}")

def format_summary_for_artisan(data_json: Dict, customer_phone: str = "") -> str:
    """Génère le texte du SMS destiné à l'artisan."""
    def get_val(key: str) -> str:
        # Extrait la valeur de la structure JSON de l'IA
        field = data_json.get(key)
        return str(field.get("value")) if isinstance(field, dict) and field.get("value") else "Non précisé"

    nom = get_val("client_nom")
    
    return (
        f"👷 NOUVELLE DEMANDE : {nom if nom != 'Non précisé' else 'Nouveau Client'}\n"
        f"🔧 PB : {get_val('probleme')}\n"
        f"📍 LIEU : {get_val('localisation')}\n"
        f"🚨 URGENCE : {get_val('urgence')}\n"
        f"📞 RAPPEL : {customer_phone}"
    )