# -*- coding: utf-8 -*-
"""
Configuration management for 4d4y CLI.
Handles loading/saving user credentials and session data.
"""

import os
import json
import hashlib
from pathlib import Path


class Config:
    """Manages configuration and credentials for 4d4y forum access."""

    # Default configuration directory
    DEFAULT_CONFIG_DIR = os.path.expanduser("~/.config/4d4y_cli")
    DEFAULT_CONFIG_FILE = "config.json"
    DEFAULT_COOKIES_FILE = "cookies.json"

    # Forum URLs
    FORUM_SERVER = "https://www.4d4y.com"
    BASE_URL = "https://www.4d4y.com/forum/"

    # Known forum IDs
    FORUMS = {
        2: "Discovery",
        6: "Buy & Sell",
        7: "Geek Talks",
        9: "Smartphone",
        12: "PalmOS",
        14: "Windows Mobile",
        22: "麦客爱苹果",
        23: "随笔与个人文集",
        24: "意欲蔓延",
        25: "吃喝玩乐",
        36: "E-INK",
        50: "DC,NB,MP3,Gadgets",
        56: "iPhone, iPod Touch, iPad",
        57: "疑似机器人",
        59: "E-INK",
        60: "Android, Chrome, & Google",
        62: "Joggler",
        63: "已完成交易",
        64: "只讨论2.0",
        65: "改版建议",
    }

    def __init__(self, config_dir=None):
        """
        Initialize configuration manager.

        Args:
            config_dir: Optional custom config directory path
        """
        self.config_dir = config_dir or self.DEFAULT_CONFIG_DIR
        self.config_path = os.path.join(self.config_dir, self.DEFAULT_CONFIG_FILE)
        self.cookies_path = os.path.join(self.config_dir, self.DEFAULT_COOKIES_FILE)
        self._config = self._load_config()

    def _ensure_config_dir(self):
        """Create config directory if it doesn't exist."""
        Path(self.config_dir).mkdir(parents=True, exist_ok=True)

    def _load_config(self):
        """Load configuration from JSON file."""
        if os.path.exists(self.config_path):
            try:
                with open(self.config_path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError):
                pass
        return self._default_config()

    def _default_config(self):
        """Return default configuration."""
        return {
            "username": "",
            "password": "",
            "logged_in": False,
            "uid": "",
            "formhash": "",
        }

    def save_config(self):
        """Save current configuration to file."""
        try:
            self._ensure_config_dir()
            with open(self.config_path, "w", encoding="utf-8") as f:
                json.dump(self._config, f, indent=2, ensure_ascii=False)
        except IOError as e:
            raise ConfigError(f"Failed to save config: {e}")

    def save_cookies(self, cookies_dict):
        """
        Save cookies for session persistence.

        Args:
            cookies_dict: Dictionary of cookie name -> value
        """
        try:
            self._ensure_config_dir()
            with open(self.cookies_path, "w", encoding="utf-8") as f:
                json.dump(cookies_dict, f, indent=2)
        except IOError as e:
            raise ConfigError(f"Failed to save cookies: {e}")

    def load_cookies(self):
        """
        Load saved cookies for session restoration.

        Returns:
            Dictionary of cookie name -> value, or empty dict if none
        """
        if os.path.exists(self.cookies_path):
            try:
                with open(self.cookies_path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError):
                pass
        return {}

    def clear_cookies(self):
        """Remove saved cookies file."""
        if os.path.exists(self.cookies_path):
            os.remove(self.cookies_path)

    @property
    def username(self):
        return self._config.get("username", "")

    @username.setter
    def username(self, value):
        self._config["username"] = value

    @property
    def password(self):
        return self._config.get("password", "")

    @password.setter
    def password(self, value):
        self._config["password"] = value

    @property
    def logged_in(self):
        return self._config.get("logged_in", False)

    @logged_in.setter
    def logged_in(self, value):
        self._config["logged_in"] = value

    @property
    def uid(self):
        return self._config.get("uid", "")

    @uid.setter
    def uid(self, value):
        self._config["uid"] = value

    @property
    def formhash(self):
        return self._config.get("formhash", "")

    @formhash.setter
    def formhash(self, value):
        self._config["formhash"] = value

    def is_logged_in(self):
        """Check if user appears to be logged in."""
        return self.logged_in and self.username


class ConfigError(Exception):
    """Configuration-related errors."""
    pass
