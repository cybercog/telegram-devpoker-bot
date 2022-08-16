from app.game import Game
import aiosqlite
import json

class GameRegistry:
    def __init__(self):
        self._db = None

    def new_game(self, chat_id, incoming_message_id: str, initiator: dict, text: str):
        return Game(chat_id, incoming_message_id, initiator, text)

    async def init_db(self, db_path):
        con = aiosqlite.connect(db_path)
        con.daemon = True
        self._db = await con
        await self._db.execute("""
            CREATE TABLE IF NOT EXISTS games (
                chat_id, game_id, 
                json_data,
                PRIMARY KEY (chat_id, game_id)
            )
        """)

    async def get_game(self, chat_id, incoming_message_id: str) -> Game:
        query = "SELECT json_data FROM games WHERE chat_id = ? AND game_id = ?"
        async with self._db.execute(query, (chat_id, incoming_message_id)) as cursor:
            result = await cursor.fetchone()
            if not result:
                return None
            return Game.from_dict(chat_id, incoming_message_id, json.loads(result[0]))

    async def save_game(self, game: Game):
        await self._db.execute(
            "INSERT OR REPLACE INTO games VALUES (?, ?, ?)",
            (game.chat_id, game.message_id, json.dumps(game.to_dict()))
        )
        await self._db.commit()
