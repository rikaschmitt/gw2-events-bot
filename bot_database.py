import os

import psycopg


DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    raise RuntimeError(
        "A variável de ambiente DATABASE_URL não foi configurada."
    )


def get_connection():
    return psycopg.connect(DATABASE_URL)


async def criar_evento(
    discord_message_id,
    discord_channel_id,
    discord_guild_id,
    event_type,
    name,
    event_date,
    event_time,
    description,
    requirements,
    lfg,
    organizer_discord_id,
    organizer_name,
):
    query = """
        INSERT INTO events (
            discord_message_id,
            discord_channel_id,
            discord_guild_id,
            type,
            name,
            event_date,
            event_time,
            description,
            requirements,
            lfg,
            organizer_discord_id,
            organizer_name
        )
        VALUES (
            %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
        )
        RETURNING id;
    """

    def executar():
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    query,
                    (
                        discord_message_id,
                        discord_channel_id,
                        discord_guild_id,
                        event_type,
                        name,
                        event_date,
                        event_time,
                        description,
                        requirements,
                        lfg,
                        organizer_discord_id,
                        organizer_name,
                    ),
                )
                return cur.fetchone()[0]

    return executar()


async def definir_participacao(
    event_id,
    discord_user_id,
    discord_username,
    participation_type,
):
    query = """
        INSERT INTO event_participants (
            event_id,
            discord_user_id,
            discord_username,
            participation_type
        )
        VALUES (%s, %s, %s, %s)
        ON CONFLICT (event_id, discord_user_id)
        DO UPDATE SET
            discord_username = EXCLUDED.discord_username,
            participation_type = EXCLUDED.participation_type;
    """

    def executar():
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    query,
                    (
                        event_id,
                        discord_user_id,
                        discord_username,
                        participation_type,
                    ),
                )

    return executar()


async def remover_participacao(
    event_id,
    discord_user_id,
):
    query = """
        DELETE FROM event_participants
        WHERE event_id = %s
          AND discord_user_id = %s;
    """

    def executar():
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    query,
                    (
                        event_id,
                        discord_user_id,
                    ),
                )

    return executar()


async def buscar_contagem_participacao(event_id):
    query = """
        SELECT
            COUNT(*) FILTER (
                WHERE participation_type = 'participant'
            ) AS participantes,
            COUNT(*) FILTER (
                WHERE participation_type = 'interested'
            ) AS interessados
        FROM event_participants
        WHERE event_id = %s;
    """

    def executar():
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(query, (event_id,))
                row = cur.fetchone()

                return {
                    "participantes": row[0],
                    "interessados": row[1],
                }

    return executar()


async def buscar_evento_por_mensagem(discord_message_id):
    query = """
        SELECT
            id,
            discord_message_id,
            discord_channel_id,
            discord_guild_id,
            type,
            name,
            event_date,
            event_time,
            description,
            requirements,
            lfg,
            organizer_discord_id,
            organizer_name,
            status
        FROM events
        WHERE discord_message_id = %s;
    """

    def executar():
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(query, (discord_message_id,))
                row = cur.fetchone()

                if row is None:
                    return None

                return {
                    "id": row[0],
                    "discord_message_id": row[1],
                    "discord_channel_id": row[2],
                    "discord_guild_id": row[3],
                    "type": row[4],
                    "name": row[5],
                    "event_date": row[6],
                    "event_time": row[7],
                    "description": row[8],
                    "requirements": row[9],
                    "lfg": row[10],
                    "organizer_discord_id": row[11],
                    "organizer_name": row[12],
                    "status": row[13],
                }

    return executar()
