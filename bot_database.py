import os
import psycopg
from datetime import datetime
from zoneinfo import ZoneInfo

TIMEZONE = ZoneInfo("America/Sao_Paulo")

DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    raise RuntimeError(
        "A variável de ambiente DATABASE_URL não foi configurada."
    )


def get_connection():
    return psycopg.connect(DATABASE_URL)


def buscar_gw2_id(discord_user_id):
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT gw2_id
                FROM users
                WHERE discord_user_id = %s
                """,
                (discord_user_id,)
            )
            row = cur.fetchone()

    return row[0] if row else None


def salvar_gw2_id(discord_user_id, discord_username, gw2_id):
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO users (
                    discord_user_id,
                    discord_username,
                    gw2_id
                )
                VALUES (%s, %s, %s)
                ON CONFLICT (discord_user_id)
                DO UPDATE SET
                    discord_username = EXCLUDED.discord_username,
                    gw2_id = EXCLUDED.gw2_id,
                    updated_at = now()
                """,
                (
                    discord_user_id,
                    discord_username,
                    gw2_id
                )
            )
        conn.commit()


def salvar_evento(
    discord_message_id,
    discord_channel_id,
    discord_guild_id,
    titulo,
    gw2_id,
    event_date,
    event_time,
    descricao,
    organizer_discord_id,
    organizer_name,
):
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO lfg_events (
                    discord_message_id,
                    discord_channel_id,
                    discord_guild_id,
                    titulo,
                    gw2_id,
                    event_date,
                    event_time,
                    descricao,
                    organizer_discord_id,
                    organizer_name
                )
                VALUES (
                    %s, %s, %s, %s, %s,
                    %s, %s, %s, %s, %s
                )
                RETURNING id
                """,
                (
                    discord_message_id,
                    discord_channel_id,
                    discord_guild_id,
                    titulo,
                    gw2_id,
                    event_date,
                    event_time,
                    descricao,
                    organizer_discord_id,
                    organizer_name,
                )
            )

            event_id = cur.fetchone()[0]

        conn.commit()

    return event_id


def buscar_meus_eventos(discord_user_id):
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT
                    id,
                    discord_message_id,
                    titulo,
                    gw2_id,
                    event_date,
                    event_time,
                    descricao,
                    status
                FROM lfg_events
                WHERE organizer_discord_id = %s
                  AND status = 'active'
                ORDER BY event_date, event_time
                LIMIT 20
                """,
                (discord_user_id,)
            )

            rows = cur.fetchall()

    agora = datetime.now(TIMEZONE)

    eventos = []

    for row in rows:
        event_date = row[4]
        event_time = row[5]

        # Comparamos usando o horário de Brasília, evitando diferenças
        # entre o fuso do PostgreSQL/Supabase e o fuso do Discord.
        inicio_evento = datetime.combine(
            event_date,
            event_time,
            tzinfo=TIMEZONE
        )

        if inicio_evento >= agora:
            eventos.append({
                "id": row[0],
                "discord_message_id": row[1],
                "titulo": row[2],
                "gw2_id": row[3],
                "event_date": event_date,
                "event_time": event_time,
                "descricao": row[6],
                "status": row[7],
            })

    return eventos


def excluir_evento(evento_id, organizer_discord_id):
    """
    Marca o evento como inativo.
    Retorna True quando o evento pertence ao usuário e foi desativado.
    """
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE lfg_events
                SET
                    status = 'deleted',
                    updated_at = now()
                WHERE id = %s
                  AND organizer_discord_id = %s
                  AND status = 'active'
                RETURNING id
                """,
                (
                    evento_id,
                    organizer_discord_id,
                )
            )

            row = cur.fetchone()

        conn.commit()

    return row is not None
