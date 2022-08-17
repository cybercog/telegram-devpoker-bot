from app.game import Game
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
                CREATE TABLE IF NOT EXISTS game (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    chat_id INTEGER NOT NULL,
                    game_message_id INTEGER NOT NULL,
                    topic_message_id INTEGER NOT NULL,
                    phase TEXT NOT NULL,
                    topic TEXT NOT NULL,
                    json_data TEXT NOT NULL
                )
            """
        )
        await self.db_connection.execute(
            """
                CREATE UNIQUE INDEX IF NOT EXISTS game_chat_id_game_message_id_idx 
                ON game (chat_id, game_message_id);
            """
        )

    async def find_game(self, chat_id: int, topic_message_id: int) -> Game:
        query = """
            SELECT json_data
            FROM game
            WHERE chat_id = ?
            AND topic_message_id = ?
            ORDER BY game_message_id DESC
            LIMIT 1
        """
        async with self.db_connection.execute(query, (chat_id, topic_message_id)) as cursor:
            result = await cursor.fetchone()

            if not result:
                return None

            return Game.from_dict(chat_id, topic_message_id, json.loads(result[0]))

    async def create_game(self, game: Game):
        await self.db_connection.execute(
            """
                INSERT INTO game
                (
                    chat_id,
                    game_message_id,
                    topic_message_id,
                    phase,
                    topic,
                    json_data
                ) VALUES (
                    ?,
                    ?,
                    ?,
                    ?,
                    ?,
                    ?
                )
            """,
            (
                game.chat_id,
                game.game_message_id,
                game.topic_message_id,
                game.phase,
                game.topic,
                json.dumps(game.to_dict()),
            )
        )
        await self.db_connection.commit()

    async def update_game(self, game: Game):
        await self.db_connection.execute(
            """
                UPDATE game
                SET phase = ?,
                    json_data = ?
                WHERE chat_id = ?
                AND game_message_id = ?
            """,
            (
                game.phase,
                json.dumps(game.to_dict()),
                game.chat_id,
                game.game_message_id,
            )
        )
        await self.db_connection.commit()
