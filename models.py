from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field
from sqlalchemy import String, Integer, DateTime, Enum as SAEnum, ForeignKey, JSON, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from db import Base

# --- Enums ---
class ConversationStatus(str, Enum):
    EN_COURS = "en_cours"
    TERMINE = "termine"

class MessageRole(str, Enum):
    CLIENT = "client"
    ASSISTANT = "assistant"

# --- Modèles SQLAlchemy ---
class Artisan(Base):
    __tablename__ = "artisans"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    nom_societe: Mapped[str] = mapped_column(String(100), nullable=False)
    twilio_phone_number: Mapped[str] = mapped_column(String(32), unique=True, index=True)
    notification_phone_number: Mapped[str] = mapped_column(String(32))
    business_hours: Mapped[Dict] = mapped_column(JSON, default=dict)
    
    conversations: Mapped[List["Conversation"]] = relationship(back_populates="artisan", cascade="all, delete-orphan")

class Conversation(Base):
    __tablename__ = "conversations"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    phone: Mapped[str] = mapped_column(String(32), index=True)
    artisan_id: Mapped[int] = mapped_column(ForeignKey("artisans.id", ondelete="CASCADE"), index=True)
    status: Mapped[ConversationStatus] = mapped_column(SAEnum(ConversationStatus), default=ConversationStatus.EN_COURS)
    data: Mapped[Dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    artisan: Mapped["Artisan"] = relationship(back_populates="conversations")
    messages: Mapped[List["Message"]] = relationship(back_populates="conversation", cascade="all, delete-orphan")

class Message(Base):
    __tablename__ = "messages"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    twilio_sid: Mapped[Optional[str]] = mapped_column(String(64), unique=True, index=True)
    conversation_id: Mapped[int] = mapped_column(ForeignKey("conversations.id", ondelete="CASCADE"), index=True)
    role: Mapped[MessageRole] = mapped_column(SAEnum(MessageRole))
    content: Mapped[str] = mapped_column(String)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    conversation: Mapped["Conversation"] = relationship(back_populates="messages")

# --- Schemas Pydantic ---
class ArtisanCreate(BaseModel):
    nom_societe: str
    twilio_phone_number: str
    notification_phone_number: str
    business_hours: Dict[str, Any] = {}