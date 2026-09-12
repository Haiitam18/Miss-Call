from __future__ import annotations
import asyncio
import json
import logging
import os
from typing import Any, Dict

from fastapi import BackgroundTasks, Depends, FastAPI, Request
from fastapi.responses import PlainTextResponse
from dotenv import load_dotenv
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from sqlalchemy.orm.attributes import flag_modified
from twilio.twiml.voice_response import VoiceResponse

from db import get_db, init_db
from models import Conversation, ConversationStatus, Message, MessageRole, Artisan
from openai_client import OpenAIWrapper
from prompts import SYSTEM_PROMPT_EXTRACT, SYSTEM_PROMPT_NEXT_QUESTION
from utils import format_summary_for_artisan, send_sms

# Configuration Logs
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv()
app = FastAPI(title="SMS Secretary - Multi-Artisan")

# --- UTILS ---

def _normalize_phone(value: str) -> str:
    """Nettoie le numéro de téléphone pour comparaison base de données."""
    return (value or "").replace("whatsapp:", "").strip()

def _is_complete(data: Dict[str, Any]) -> bool:
    """Vérifie si les informations essentielles sont présentes."""
    if not data: return False
    
    def is_valid(field: str) -> bool:
        val = data.get(field, {}).get("value")
        if not isinstance(val, str): return False
        v = val.strip().lower()
        if field == "urgence": return v in ["faible", "moyenne", "haute"]
        return v not in ["", "null", "none", "unknown"] and len(v) > 1
        
    return is_valid("probleme") and is_valid("urgence") and is_valid("localisation")

async def _get_or_create_conversation(session: AsyncSession, phone: str, artisan_id: int) -> Conversation:
    stmt = select(Conversation).where(
        Conversation.phone == phone, 
        Conversation.artisan_id == artisan_id
    ).order_by(Conversation.id.desc())
    conv = (await session.execute(stmt)).scalars().first()

    if not conv or conv.status == ConversationStatus.TERMINE:
        conv = Conversation(phone=phone, artisan_id=artisan_id, status=ConversationStatus.EN_COURS, data={})
        session.add(conv)
        await session.commit()
        await session.refresh(conv)
    return conv

async def _store_message(session: AsyncSession, **kwargs) -> None:
    session.add(Message(**kwargs))
    await session.commit()

# --- LOGIQUE IA ---

_conversation_locks: Dict[int, asyncio.Lock] = {}

async def process_ai_logic(from_number: str, body: str, conv_id: int):
    lock = _conversation_locks.setdefault(conv_id, asyncio.Lock())
    async with lock:
        async for session in get_db():
            try:
                stmt = select(Conversation).options(selectinload(Conversation.artisan)).where(Conversation.id == conv_id)
                conv = (await session.execute(stmt)).scalars().first()
                if not conv or conv.status == ConversationStatus.TERMINE: return

                artisan = conv.artisan
                wrapper = OpenAIWrapper(api_key=os.getenv("OPENAI_API_KEY"), model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"))

                # Extraction des données
                new_extracted = await wrapper.chat_completion_json([
                    {"role": "system", "content": SYSTEM_PROMPT_EXTRACT.format(nom_societe=artisan.nom_societe)},
                    {"role": "user", "content": f"Contexte: {json.dumps(conv.data)}\nMessage: {body}"}
                ])
                
                # Fusion des données
                new_data = json.loads(new_extracted) if isinstance(new_extracted, str) else new_extracted
                if new_data:
                    for key, item in new_data.items():
                        if not isinstance(item, dict): item = {"value": item, "confidence": 1.0}
                        if item.get("value"): conv.data[key] = item
                    flag_modified(conv, "data")
                    await session.commit()

                # Décision : Envoyer le dossier ou continuer la discussion
                if _is_complete(conv.data) and not conv.data.get("_dossier_envoye"):
                    conv.data["_dossier_envoye"] = True
                    flag_modified(conv, "data")
                    await session.commit()
                    
                    summary = format_summary_for_artisan(conv.data, customer_phone=from_number)
                    await send_sms(artisan.notification_phone_number, f"📢 NOUVEAU DOSSIER ({artisan.nom_societe}) :\n\n{summary}")
                    await send_sms(from_number, f"Merci ! ✅ Votre demande est transmise à {artisan.nom_societe}.")
                else:
                    resp = await wrapper.chat_completion([{"role": "system", "content": SYSTEM_PROMPT_NEXT_QUESTION.format(
                        nom_societe=artisan.nom_societe, data_json=json.dumps(conv.data), last_message=body
                    )}])
                    await _store_message(session, conversation_id=conv.id, role=MessageRole.ASSISTANT, content=resp)
                    await send_sms(from_number, resp)
            except Exception:
                logger.exception("Erreur dans process_ai_logic pour %s (conv_id=%s)", from_number, conv_id)
                try:
                    await send_sms(from_number, "Un instant, votre demande est bien prise en compte, nous revenons vers vous.")
                except Exception:
                    pass

# --- WEBHOOKS ---

@app.post("/sms/reply/", response_class=PlainTextResponse)
async def webhook_messages(request: Request, background: BackgroundTasks, session: AsyncSession = Depends(get_db)):
    form = await request.form()
    from_number, to_number = _normalize_phone(form.get("From")), _normalize_phone(form.get("To"))
    body = (form.get("Body") or "").strip()

    artisan = (await session.execute(select(Artisan).where(Artisan.twilio_phone_number == to_number))).scalars().first()
    if not artisan: return "Artisan non configuré"

    conv = await _get_or_create_conversation(session, from_number, artisan.id)
    await _store_message(session, conversation_id=conv.id, role=MessageRole.CLIENT, content=body)

    # Message de bienvenue si conversation vide
    if not (await session.execute(select(Message).where(Message.conversation_id == conv.id, Message.role == MessageRole.ASSISTANT))).first():
        welcome = f"Bonjour, ici l'assistant de {artisan.nom_societe} 👋. L'artisan est en intervention. Pour organiser le rappel, précisez-moi : problème, ville, et urgence."
        await _store_message(session, conversation_id=conv.id, role=MessageRole.ASSISTANT, content=welcome)
        await send_sms(from_number, welcome)
        return ""

    background.add_task(process_ai_logic, from_number, body, conv.id)
    return ""

@app.post("/welcome/voice/", response_class=PlainTextResponse)
async def webhook_voice(request: Request, session: AsyncSession = Depends(get_db)):
    form = await request.form()
    from_number, to_number = _normalize_phone(form.get("From")), _normalize_phone(form.get("To"))

    artisan = (await session.execute(select(Artisan).where(Artisan.twilio_phone_number == to_number))).scalars().first()
    if artisan:
        conv = await _get_or_create_conversation(session, from_number, artisan.id)
        if not (await session.execute(select(Message).where(Message.conversation_id == conv.id, Message.role == MessageRole.ASSISTANT))).first():
            welcome = f"Bonjour, ici l'assistant de {artisan.nom_societe} 👋. Précisez-moi votre problème, votre ville et si c'est une urgence pour organiser votre rappel."
            await _store_message(session, conversation_id=conv.id, role=MessageRole.ASSISTANT, content=welcome)
            await send_sms(from_number, welcome)

    response = VoiceResponse()
    response.reject(reason='busy')
    return str(response)

@app.on_event("startup")
async def _startup():
    await init_db()