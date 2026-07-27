from datetime import datetime
from .database import Settings


DEFAULT_SETTINGS = [
    ("security.min_password_length", "6", "Minimum password length"),
    ("security.require_2fa", "false", "Require two-factor authentication for all users"),
    ("security.session_timeout_minutes", "30", "Session timeout in minutes"),
    ("ui.dark_mode", "false", "Enable dark mode"),
    ("ui.language", "zh-CN", "UI language"),
    ("agent.default_commission_rate", "0", "Default agent commission rate (%)"),
    ("agent.default_max_devices", "0", "Default max devices per agent (0=unlimited)"),
    ("retention.device_days", "0", "Device data retention in days (0=forever)"),
    ("retention.log_days", "90", "Log data retention in days"),
    ("notifications.email_alerts", "false", "Send email alerts"),
    ("modules.commands_enabled", "true", "Enable commands module"),
    ("modules.wallets_enabled", "true", "Enable wallets module"),
    ("sensitive.commands_2fa", "false", "Require 2FA for command operations"),
    ("sensitive.wallets_2fa", "false", "Require 2FA for wallet operations"),
    ("sensitive.users_2fa", "false", "Require 2FA for user management"),
    ("sensitive.agents_2fa", "false", "Require 2FA for agent management"),
    ("sensitive.profile_2fa", "false", "Require 2FA for profile changes"),
    ("modules.exif_categories_enabled", "keychain,wifi,contacts,sms,calls,photos,files,clipboard,notes,wallets", "Enabled exfil categories"),
]


def ensure_default_settings(db):
    changed = False
    for key, default_value, description in DEFAULT_SETTINGS:
        existing = db.query(Settings).filter(Settings.key == key).first()
        if not existing:
            stg = Settings(
                key=key, value=str(default_value), description=description,
                updated_at=datetime.now()
            )
            db.add(stg)
            changed = True
    if changed:
        db.commit()


def get_setting(db, key: str, default=None):
    s = db.query(Settings).filter(Settings.key == key).first()
    return s.value if s else default


def set_setting(db, key: str, value: str, description: str = None):
    s = db.query(Settings).filter(Settings.key == key).first()
    if not s:
        s = Settings(key=key, value=value, description=description, updated_at=datetime.now())
        db.add(s)
    else:
        s.value = value
        if description:
            s.description = description
        s.updated_at = datetime.now()
    db.commit()
    return s
