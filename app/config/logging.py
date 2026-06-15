import logging
import os
import shutil
from logging.handlers import RotatingFileHandler
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings


class _WindowsSafeRotatingFileHandler(RotatingFileHandler):
    """RotatingFileHandler compatible Windows.

    Sur Windows, os.rename échoue si le fichier est ouvert par n'importe quel
    processus. On remplace la rotation par copy2 + truncate : le fichier de
    destination reçoit le contenu courant, puis la source est vidée sans être
    renommée — les handles existants restent valides.
    """

    def rotate(self, source: str, dest: str) -> None:
        if os.path.exists(dest):
            os.remove(dest)
        shutil.copy2(source, dest)
        # Vide le fichier source en place — aucun rename, aucun WinError 32.
        with open(source, "w", encoding="utf-8"):
            pass


class LoggingSettings(BaseSettings):
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = Field(
        default="INFO", description="Niveau de log (DEBUG, INFO, WARNING, ERROR)"
    )
    log_file_path: str = Field(default="logs/app.log", description="Chemin du fichier de log")
    log_max_bytes: int = Field(
        default=10485760,
        description="Taille maximale d'un fichier de log (10MB par défaut)",
    )
    log_backup_count: int = Field(default=5, description="Nombre de fichiers de backup à conserver")
    log_to_console: bool = Field(default=True, description="Activer les logs dans la console")
    log_to_file: bool = Field(default=True, description="Activer les logs dans un fichier")

    model_config = {
        "env_file": ".env",
        "case_sensitive": False,
        "extra": "ignore",
    }

    def __repr__(self) -> str:
        return f"<BaseSettings log={self.log_level} path={self.log_file_path}>"

    def setup_logging(self, logger_name: str | None = None) -> logging.Logger:
        logger = logging.getLogger(logger_name)

        if logger.handlers:
            return logger

        logger.setLevel(getattr(logging, self.log_level))

        # Format des logs
        formatter = logging.Formatter(
            fmt="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )

        if self.log_to_console:
            console_handler = logging.StreamHandler()
            console_handler.setLevel(getattr(logging, self.log_level))
            console_handler.setFormatter(formatter)
            logger.addHandler(console_handler)

        if self.log_to_file:  # Rotation file
            log_dir = os.path.dirname(self.log_file_path)
            if log_dir:
                os.makedirs(log_dir, exist_ok=True)

            file_handler = _WindowsSafeRotatingFileHandler(
                filename=self.log_file_path,
                maxBytes=self.log_max_bytes,
                backupCount=self.log_backup_count,
                encoding="utf-8",
            )
            file_handler.setLevel(getattr(logging, self.log_level))
            file_handler.setFormatter(formatter)
            logger.addHandler(file_handler)

        # Empêcher la propagation au logger parent
        logger.propagate = False

        return logger

    def get_logger(self, name: str) -> logging.Logger:
        return self.setup_logging(name)

    @property
    def logger(self) -> logging.Logger:
        return self.get_logger("app")
