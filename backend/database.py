import re
from datetime import datetime

import mysql.connector
from mysql.connector import Error

from config import (
    DB_HOST,
    DB_NAME,
    DB_PASSWORD,
    DB_PORT,
    DB_SESSION_TTL_HOURS,
    DB_USER,
)


class DatabaseUnavailable(RuntimeError):
    pass


def _validated_db_name() -> str:
    if not re.fullmatch(r"[A-Za-z0-9_]+", DB_NAME):
        raise DatabaseUnavailable(
            "DB_NAME inválido. Use somente letras, números e underscore (_)."
        )
    return DB_NAME


def _connect(use_database: bool = True):
    config = {
        "host": DB_HOST,
        "port": DB_PORT,
        "user": DB_USER,
        "password": DB_PASSWORD,
        "connection_timeout": 5,
        "charset": "utf8mb4",
    }
    if use_database:
        config["database"] = _validated_db_name()
    try:
        return mysql.connector.connect(**config)
    except Error as exc:
        raise DatabaseUnavailable(str(exc)) from exc


def initialize() -> None:
    """Cria o banco e as tabelas automaticamente e limpa sessões antigas."""
    db_name = _validated_db_name()

    connection = _connect(use_database=False)
    cursor = connection.cursor()
    try:
        cursor.execute(
            f"CREATE DATABASE IF NOT EXISTS `{db_name}` "
            "CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"
        )
        connection.commit()
    finally:
        cursor.close()
        connection.close()

    connection = _connect()
    cursor = connection.cursor()
    try:
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS sessoes (
                session_id VARCHAR(64) PRIMARY KEY,
                criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                ultima_atividade TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    ON UPDATE CURRENT_TIMESTAMP
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
            """
        )
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS respostas_salvas (
                id INT AUTO_INCREMENT PRIMARY KEY,
                session_id VARCHAR(64) NOT NULL,
                pergunta TEXT NOT NULL,
                resposta LONGTEXT NOT NULL,
                criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                INDEX idx_respostas_session (session_id),
                CONSTRAINT fk_respostas_sessao
                    FOREIGN KEY (session_id)
                    REFERENCES sessoes(session_id)
                    ON DELETE CASCADE
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
            """
        )
        # Segurança para sessões que não foram encerradas corretamente pelo navegador.
        # Apaga primeiro as respostas para também funcionar com bancos criados
        # por versões anteriores do projeto que ainda não tinham a FK CASCADE.
        cursor.execute(
            f"""
            DELETE r FROM respostas_salvas r
            INNER JOIN sessoes s ON s.session_id = r.session_id
            WHERE s.ultima_atividade < (NOW() - INTERVAL {DB_SESSION_TTL_HOURS} HOUR)
            """
        )
        cursor.execute(
            f"DELETE FROM sessoes "
            f"WHERE ultima_atividade < (NOW() - INTERVAL {DB_SESSION_TTL_HOURS} HOUR)"
        )
        connection.commit()
    finally:
        cursor.close()
        connection.close()


def ping() -> bool:
    connection = None
    try:
        connection = _connect()
        return bool(connection.is_connected())
    except DatabaseUnavailable:
        return False
    finally:
        if connection and connection.is_connected():
            connection.close()


def _touch_session(cursor, session_id: str) -> None:
    cursor.execute(
        """
        INSERT INTO sessoes (session_id)
        VALUES (%s)
        ON DUPLICATE KEY UPDATE ultima_atividade = CURRENT_TIMESTAMP
        """,
        (session_id,),
    )


def save_response(session_id: str, question: str, answer: str) -> int:
    connection = _connect()
    cursor = connection.cursor()
    try:
        _touch_session(cursor, session_id)
        cursor.execute(
            """
            INSERT INTO respostas_salvas (session_id, pergunta, resposta)
            VALUES (%s, %s, %s)
            """,
            (session_id, question, answer),
        )
        connection.commit()
        return int(cursor.lastrowid)
    except Error as exc:
        connection.rollback()
        raise DatabaseUnavailable(str(exc)) from exc
    finally:
        cursor.close()
        connection.close()


def list_responses(session_id: str) -> list[dict]:
    connection = _connect()
    cursor = connection.cursor(dictionary=True)
    try:
        _touch_session(cursor, session_id)
        cursor.execute(
            """
            SELECT id, pergunta, resposta, criado_em
            FROM respostas_salvas
            WHERE session_id = %s
            ORDER BY id DESC
            """,
            (session_id,),
        )
        rows = cursor.fetchall()
        connection.commit()
        for row in rows:
            value = row.get("criado_em")
            if isinstance(value, datetime):
                row["criado_em"] = value.isoformat(timespec="seconds")
        return rows
    except Error as exc:
        connection.rollback()
        raise DatabaseUnavailable(str(exc)) from exc
    finally:
        cursor.close()
        connection.close()


def delete_response(session_id: str, response_id: int) -> bool:
    connection = _connect()
    cursor = connection.cursor()
    try:
        cursor.execute(
            "DELETE FROM respostas_salvas WHERE id = %s AND session_id = %s",
            (response_id, session_id),
        )
        deleted = cursor.rowcount > 0
        connection.commit()
        return deleted
    except Error as exc:
        connection.rollback()
        raise DatabaseUnavailable(str(exc)) from exc
    finally:
        cursor.close()
        connection.close()


def clear_responses(session_id: str) -> int:
    connection = _connect()
    cursor = connection.cursor()
    try:
        cursor.execute(
            "DELETE FROM respostas_salvas WHERE session_id = %s",
            (session_id,),
        )
        deleted = cursor.rowcount
        connection.commit()
        return int(deleted)
    except Error as exc:
        connection.rollback()
        raise DatabaseUnavailable(str(exc)) from exc
    finally:
        cursor.close()
        connection.close()


def close_session(session_id: str) -> None:
    connection = _connect()
    cursor = connection.cursor()
    try:
        # Remove explicitamente as respostas para manter compatibilidade com
        # tabelas criadas por versões anteriores que não tinham ON DELETE CASCADE.
        cursor.execute(
            "DELETE FROM respostas_salvas WHERE session_id = %s",
            (session_id,),
        )
        cursor.execute("DELETE FROM sessoes WHERE session_id = %s", (session_id,))
        connection.commit()
    except Error as exc:
        connection.rollback()
        raise DatabaseUnavailable(str(exc)) from exc
    finally:
        cursor.close()
        connection.close()
