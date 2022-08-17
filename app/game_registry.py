from app.game import Game
import aiosqlite
import json

class GameRegistry:
    def __init__(self):
        self.db_connection = None

    def new_game(self, chat_id, message_id: str, initiator: dict, text: str):
        return Game(chat_id, message_id, initiator, text)

    async def init_db(self, db_path):
        connection = aiosqlite.connect(db_path)
        connection.daemon = True
        self.db_connection = await connection
        await self.run_migrations()

    async def run_migrations(self):
        await self.db_connection.execute(
            """
                CREATE TABLE IF NOT EXISTS game (
                    chat_id,
                    message_id,
                    json_data,
                    PRIMARY KEY (chat_id, message_id)
                )
            """
        )

    async def get_game(self, chat_id, message_id: str) -> Game:
        query = """
            SELECT json_data
            FROM game
            WHERE chat_id = ?
            AND message_id = ?
        """
        async with self.db_connection.execute(query, (chat_id, message_id)) as cursor:
            result = await cursor.fetchone()

            if not result:
                return None

            return Game.from_dict(chat_id, message_id, json.loads(result[0]))

    async def save_game(self, game: Game):
        await self.db_connection.execute(
            """
                INSERT OR REPLACE INTO game
                (
                    chat_id,
                    message_id,
                    json_data
                ) VALUES (
                    ?,
                    ?,
                    ?
                )
            """,
            (
                game.chat_id,
                game.message_id,
                json.dumps(game.to_dict()),
            )
        )
        await self.db_connection.commit()
