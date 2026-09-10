import os
import psycopg


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
