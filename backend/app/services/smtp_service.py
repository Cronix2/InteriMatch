"""
InteriMatch AI - Service d'envoi SMTP (gratuit).

Utilise aiosmtplib pour envoyer un email via le SMTP configuré au niveau
utilisateur (UserSettings) avec fallback sur le SMTP global (.env).

Aucun service tiers payant : compatible Gmail (mot de passe d'application),
Outlook/365, Mailtrap, OVH, Brevo SMTP, MailerSend, etc.
"""

from __future__ import annotations

import asyncio
import logging
import re
import smtplib
from dataclasses import dataclass
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.utils import formataddr, formatdate, make_msgid
from typing import Iterable

import aiosmtplib

from app.core.config import get_settings

logger = logging.getLogger(__name__)
_settings = get_settings()

_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


@dataclass
class SmtpConfig:
    host: str
    port: int
    user: str
    password: str
    use_tls: bool
    sender: str

    @property
    def is_complete(self) -> bool:
        return bool(self.host and self.port and self.sender)


class SmtpNotConfiguredError(RuntimeError):
    """Levée quand aucune config SMTP utilisable n'est trouvée."""


class SmtpSendError(RuntimeError):
    """Levée pour toute erreur d'envoi SMTP (avec message exploitable côté UI)."""


def _bool(v) -> bool:
    if isinstance(v, bool):
        return v
    if isinstance(v, str):
        return v.strip().lower() in ("1", "true", "yes", "on")
    return bool(v)


def resolve_smtp_config(user_settings) -> SmtpConfig:
    """
    Construit la SmtpConfig effective : valeurs user_settings si fournies,
    sinon valeurs globales du .env.
    """
    def pick(attr: str, env_value):
        if user_settings is None:
            return env_value
        v = getattr(user_settings, attr, None)
        if v is None:
            return env_value
        if isinstance(v, str) and not v.strip():
            return env_value
        return v

    host = (pick("smtp_host", _settings.smtp_host) or "").strip()
    raw_port = pick("smtp_port", _settings.smtp_port)
    try:
        port = int(raw_port) if raw_port else 0
    except (TypeError, ValueError):
        port = 0
    user = (pick("smtp_user", _settings.smtp_user) or "").strip()
    password = pick("smtp_password", _settings.smtp_password) or ""
    use_tls = _bool(pick("smtp_use_tls", _settings.smtp_use_tls))
    sender = (pick("smtp_from", _settings.smtp_from) or user or "").strip()

    return SmtpConfig(
        host=host,
        port=port,
        user=user,
        password=password,
        use_tls=use_tls,
        sender=sender,
    )


def _split_recipients(value: str | None) -> list[str]:
    if not value:
        return []
    parts = re.split(r"[,;\s]+", value)
    return [p.strip() for p in parts if p.strip() and _EMAIL_RE.match(p.strip())]


def _build_message(
    *,
    subject: str,
    body: str,
    sender_display_name: str,
    sender_email: str,
    recipients: list[str],
    reply_to: str | None,
    attachments: Iterable[tuple[str, bytes, str]] = (),
) -> MIMEMultipart:
    msg = MIMEMultipart()
    msg["Subject"] = subject or ""
    msg["From"] = formataddr((sender_display_name or "", sender_email))
    msg["To"] = ", ".join(recipients)
    msg["Date"] = formatdate(localtime=True)
    msg["Message-ID"] = make_msgid()
    if reply_to and _EMAIL_RE.match(reply_to):
        msg["Reply-To"] = reply_to

    msg.attach(MIMEText(body or "", "plain", "utf-8"))

    for filename, content, subtype in attachments:
        part = MIMEApplication(content, _subtype=subtype)
        part.add_header(
            "Content-Disposition",
            "attachment",
            filename=filename,
        )
        msg.attach(part)

    return msg


async def send_email_smtp(
    *,
    user_settings,
    subject: str,
    body: str,
    recipients: str | list[str],
    sender_display_name: str = "",
    reply_to: str | None = None,
    attachments: Iterable[tuple[str, bytes, str]] = (),
) -> dict:
    """
    Envoie un email via SMTP. Retourne {"recipients": [...], "message_id": "..."}.
    Lève SmtpNotConfiguredError ou SmtpSendError en cas d'échec.

    `attachments` : iterable de (filename, content_bytes, subtype) — ex:
    ("cv_anonymise.pdf", b"...", "pdf").
    """
    cfg = resolve_smtp_config(user_settings)
    if not cfg.is_complete:
        raise SmtpNotConfiguredError(
            "Configuration SMTP incomplète. Renseignez SMTP_HOST, SMTP_PORT et "
            "SMTP_FROM (Paramètres → SMTP ou .env)."
        )

    if isinstance(recipients, str):
        recipient_list = _split_recipients(recipients)
    else:
        recipient_list = [r for r in recipients if _EMAIL_RE.match(r)]
    if not recipient_list:
        raise SmtpSendError("Aucun destinataire valide.")

    msg = _build_message(
        subject=subject,
        body=body,
        sender_display_name=sender_display_name,
        sender_email=cfg.sender,
        recipients=recipient_list,
        reply_to=reply_to,
        attachments=attachments,
    )
    message_id = msg["Message-ID"]

    # Détecte le mode TLS :
    # - port 465 : SSL/TLS implicite
    # - port 587 (ou autre) avec use_tls=True : STARTTLS
    use_ssl = cfg.port == 465
    use_starttls = cfg.use_tls and not use_ssl

    try:
        await aiosmtplib.send(
            msg,
            hostname=cfg.host,
            port=cfg.port,
            username=cfg.user or None,
            password=cfg.password or None,
            use_tls=use_ssl,
            start_tls=use_starttls,
            timeout=30,
        )
    except aiosmtplib.SMTPAuthenticationError as e:
        logger.warning("SMTP auth failed for %s: %s", cfg.host, e)
        raise SmtpSendError(
            "Authentification SMTP refusée. Vérifiez l'utilisateur et le mot de passe."
        ) from e
    except aiosmtplib.SMTPConnectError as e:
        logger.warning("SMTP connect failed to %s:%s: %s", cfg.host, cfg.port, e)
        raise SmtpSendError(
            f"Connexion SMTP impossible vers {cfg.host}:{cfg.port}."
        ) from e
    except aiosmtplib.SMTPException as e:
        logger.warning("SMTP error: %s", e)
        raise SmtpSendError(f"Erreur SMTP : {e}") from e
    except (asyncio.TimeoutError, smtplib.SMTPException) as e:
        logger.warning("SMTP timeout/error: %s", e)
        raise SmtpSendError(f"Timeout ou erreur réseau : {e}") from e
    except Exception as e:  # pragma: no cover - safety net
        logger.exception("SMTP unexpected error: %s", e)
        raise SmtpSendError(f"Erreur inattendue lors de l'envoi : {e}") from e

    logger.info(
        "SMTP send OK via %s:%s -> %d recipient(s)",
        cfg.host, cfg.port, len(recipient_list),
    )
    return {"recipients": recipient_list, "message_id": message_id or ""}
