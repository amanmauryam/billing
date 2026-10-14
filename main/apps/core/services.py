"""Backup and restore services for the SQLite database.

Backups use SQLite's online backup API so a consistent snapshot is produced
even while the application is running. Restore validates the candidate file,
saves a safety backup of the current database, then replaces it.
"""

import shutil
import sqlite3
from datetime import datetime
from pathlib import Path

from django.conf import settings


class BackupError(Exception):
    """A user-facing backup or restore failure."""


def get_backup_dir() -> Path:
    directory = Path(settings.BACKUP_DIR)
    directory.mkdir(parents=True, exist_ok=True)
    return directory


def get_database_path() -> Path:
    db_name = settings.DATABASES["default"]["NAME"]
    return Path(db_name)


def _timestamp() -> str:
    return datetime.now().strftime("%Y%m%d-%H%M%S")


def create_backup(*, label: str = "backup") -> Path:
    """Create a consistent timestamped SQLite backup and return its path."""
    source = get_database_path()
    if not source.exists():
        raise BackupError(
            "Database file not found. Start the application so it can be created."
        )

    backup_dir = get_backup_dir()
    destination = backup_dir / f"pos-{label}-{_timestamp()}.sqlite3"

    source_conn = None
    dest_conn = None
    try:
        source_conn = sqlite3.connect(str(source))
        dest_conn = sqlite3.connect(str(destination))
        source_conn.backup(dest_conn)
    except sqlite3.Error as exc:
        raise BackupError(f"Backup failed: {exc}") from exc
    finally:
        if dest_conn is not None:
            dest_conn.close()
        if source_conn is not None:
            source_conn.close()

    if not destination.exists() or destination.stat().st_size == 0:
        raise BackupError("Backup failed: the backup file was not created.")

    return destination


def list_backups() -> list[dict]:
    backup_dir = get_backup_dir()
    items = []
    for path in sorted(backup_dir.glob("*.sqlite3"), reverse=True):
        stat = path.stat()
        items.append(
            {
                "name": path.name,
                "path": str(path),
                "size_kb": round(stat.st_size / 1024, 1),
                "modified": datetime.fromtimestamp(stat.st_mtime),
            }
        )
    return items


def _validate_sqlite_file(path: Path) -> None:
    if not path.exists():
        raise BackupError("The selected backup file does not exist.")
    try:
        connection = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
        try:
            result = connection.execute("PRAGMA integrity_check;").fetchone()
        finally:
            connection.close()
    except sqlite3.Error as exc:
        raise BackupError(f"Not a readable SQLite database: {exc}") from exc
    if not result or result[0] != "ok":
        raise BackupError("The selected file failed the SQLite integrity check.")

    connection = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
    try:
        tables = {
            row[0]
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type='table';"
            )
        }
    finally:
        connection.close()
    expected = {"core_shopsettings", "billing_sale", "products_product"}
    if not (tables & expected):
        raise BackupError("The selected file does not look like a POS database.")


def restore_backup(backup_path) -> Path:
    """Restore the database from ``backup_path`` after a safety backup.

    Returns the path of the safety backup that was taken first.
    """
    candidate = Path(backup_path)
    _validate_sqlite_file(candidate)

    database = get_database_path()
    if database.exists():
        safety = create_backup(label="pre-restore")
    else:
        safety = None

    try:
        shutil.copyfile(candidate, database)
    except OSError as exc:
        raise BackupError(
            f"Restore failed while copying the database: {exc}"
        ) from exc

    if safety is None:
        # Ensure the returned value is always a path-like for the caller.
        safety = database
    return safety
