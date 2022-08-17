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
                    chat_id,
                    game_message_id,
                    topic_message_id,
                    phase,
                    topic,
                    json_data,
                    PRIMARY KEY (chat_id, game_message_id)
                )
            """
        )

    async def find_game(self, chat_id: int, game_message_id: int) -> Game:
        query = """
            SELECT json_data, topic_message_id
            FROM game
            WHERE chat_id = ?
            AND game_message_id = ?
        """
        async with self.db_connection.execute(query, (chat_id, game_message_id)) as cursor:
            result = await cursor.fetchone()

            if not result:
                return None

            return Game.from_dict(chat_id, game_message_id, result[1], json.loads(result[0]))

    async def save_game(self, game: Game):
        await self.db_connection.execute(
            """
                INSERT OR REPLACE INTO game
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
