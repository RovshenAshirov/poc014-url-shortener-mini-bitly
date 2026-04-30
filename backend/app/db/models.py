from datetime import datetime
from sqlalchemy import BigInteger, Boolean, String, Text, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column
from app.db.database import Base

class URL(Base):
    __tablename__ = "urls"

    id:          Mapped[int]      = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    short_code:  Mapped[str]      = mapped_column(String(20), unique=True, nullable=False, index=True)
    long_url:    Mapped[str]      = mapped_column(Text, nullable=False)
    is_custom:   Mapped[bool]     = mapped_column(Boolean, default=False)
    click_count: Mapped[int]      = mapped_column(BigInteger, default=0)
    created_at:  Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    expires_at:  Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
