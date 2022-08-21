from app.game_session import GameSession
import aiosqlite
import json


class GameRegistry:
    def __init__(self):
        self.db_connection = None

    async def init_db(self, db_path):
        db_connection = aiosqlite.connect(db_path)
        db_connection.daemon = True
        self.db_connection = await db_connection
        await self.run_migrations()

    async def run_migrations(self):
        await self.db_connection.execute(
            """
                CREATE TABLE IF NOT EXISTS game_session (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    game_id INTEGER NOT NULL,
                    chat_id INTEGER NOT NULL,
                    facilitator_message_id INTEGER NOT NULL,
                    system_message_id INTEGER NOT NULL,
                    phase TEXT NOT NULL,
                    topic TEXT NOT NULL,
                    json_data TEXT NOT NULL,
                    created_at DATETIME NOT NULL,
                    updated_at DATETIME NOT NULL
                )
            """
        )
        await self.db_connection.execute(
            """
                CREATE UNIQUE INDEX IF NOT EXISTS game_session_chat_id_system_message_id_idx 
                ON game_session (chat_id, system_message_id);
            """
        )

    async def find_active_game_session(self, chat_id: int, facilitator_message_id: int) -> GameSession:
        query = """
            SELECT json_data
            FROM game_session
            WHERE chat_id = ?
            AND facilitator_message_id = ?
            ORDER BY system_message_id DESC
            LIMIT 1
        """
        async with self.db_connection.execute(query, (chat_id, facilitator_message_id)) as cursor:
            result = await cursor.fetchone()

            if not result:
                return None

            return GameSession.from_dict(0, chat_id, facilitator_message_id, json.loads(result[0]))

    async def create_game_session(self, game_session: GameSession):
        await self.db_connection.execute(
            """
                INSERT INTO game_session
                (
                    game_id,
                    chat_id,
                    facilitator_message_id,
                    system_message_id,
                    phase,
                    topic,
                    json_data,
                    created_at,
                    updated_at
                ) VALUES (
                    ?,
                    ?,
                    ?,
                    ?,
                    ?,
                    ?,
                    ?,
                    datetime('now'),
                    datetime('now')
                )
            """,
            (
                game_session.game_id,
                game_session.chat_id,
                game_session.facilitator_message_id,
                game_session.system_message_id,
                game_session.phase,
                game_session.topic,
                json.dumps(game_session.to_dict()),
            )
        )
        await self.db_connection.commit()

    async def update_game_session(self, game_session: GameSession):
        await self.db_connection.execute(
            """
                UPDATE game_session
                SET phase = ?,
                    json_data = ?,
                    updated_at = datetime('now')
                WHERE chat_id = ?
                AND system_message_id = ?
            """,
            (
                game_session.phase,
                json.dumps(game_session.to_dict()),
                game_session.chat_id,
                game_session.system_message_id,
            )
        )
        await self.db_connection.commit()
