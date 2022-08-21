from app.game import Game
from app.game_session import GameSession
from app.telegram_user import TelegramUser
import aiosqlite
import json


class GameRegistry:
    def __init__(self):
        self.db_connection = None

    async def init_db(self, db_path: str):
        db_connection = aiosqlite.connect(db_path)
        db_connection.daemon = True
        self.db_connection = await db_connection
        self.db_connection.row_factory = aiosqlite.Row
        await self.run_migrations()

    async def run_migrations(self):
        await self.db_connection.execute(
            """
                CREATE TABLE IF NOT EXISTS game (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    chat_id INTEGER NOT NULL,
                    facilitator_id INTEGER NOT NULL,
                    facilitator_message_id INTEGER NOT NULL,
                    system_message_id INTEGER NOT NULL,
                    status TEXT NOT NULL,
                    name TEXT NOT NULL,
                    json_data TEXT NOT NULL,
                    created_at DATETIME NOT NULL,
                    updated_at DATETIME NOT NULL
                )
            """
        )

        await self.db_connection.execute(
            """
                CREATE TABLE IF NOT EXISTS game_session (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    game_id INTEGER,
                    chat_id INTEGER NOT NULL,
                    facilitator_id INTEGER NOT NULL,
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

    async def create_game(self, game: Game):
        await self.db_connection.execute(
            """
                INSERT INTO game
                (
                    chat_id,
                    facilitator_id,
                    facilitator_message_id,
                    system_message_id,
                    status,
                    name,
                    json_data,
                    created_at,
                    updated_at
                ) VALUES (
                    :chat_id,
                    :facilitator_id,
                    :facilitator_message_id,
                    :system_message_id,
                    :status,
                    :name,
                    :json_data,
                    datetime('now'),
                    datetime('now')
                )
            """,
            {
                "chat_id": game.chat_id,
                "facilitator_id": game.facilitator.id,
                "facilitator_message_id": game.facilitator_message_id,
                "system_message_id": game.system_message_id,
                "status": game.status,
                "name": game.name,
                "json_data": json.dumps(game.to_dict()),
            }
        )
        await self.db_connection.commit()

    async def end_game(self, game: Game):
        await self.db_connection.execute(
            """
                UPDATE game
                SET status = :game_status
                WHERE id = :game_id
            """,
            {
                "game_id": game.id,
                "game_status": game.STATUS_ENDED,
            }
        )
        await self.db_connection.commit()

        game.status = Game.STATUS_ENDED

    async def find_active_game(self, chat_id: int, facilitator: TelegramUser) -> Game:
        query = """
            SELECT
                id AS game_id,
                facilitator_message_id AS game_facilitator_message_id,
                system_message_id AS game_system_message_id,
                status AS game_status,
                name AS game_name,
                json_data AS game_json_data
            FROM game
            WHERE chat_id = :chat_id
            AND facilitator_id = :game_facilitator_id
            AND status = :active_game_status
            ORDER BY system_message_id DESC
            LIMIT 1
        """
        parameters = {
            "chat_id": chat_id,
            "game_facilitator_id": facilitator.id,
            "active_game_status": Game.STATUS_STARTED,
        }
        async with self.db_connection.execute(query, parameters) as cursor:
            row = await cursor.fetchone()

            if not row:
                return None

            game_json_data = json.loads(row["game_json_data"])
            game_facilitator = TelegramUser.from_dict(game_json_data["facilitator"])

            game = Game.from_dict(
                chat_id,
                row["game_facilitator_message_id"],
                row["game_name"],
                game_facilitator,
            )
            game.id = row["game_id"]
            game.system_message_id = row["game_system_message_id"]
            game.status = row["game_status"]

            return game

    async def find_active_game_session(self, chat_id: int, game_session_facilitator_message_id: int) -> GameSession:
        query = """
            SELECT
                g.id AS game_id,
                g.facilitator_message_id AS game_facilitator_message_id,
                g.system_message_id AS game_system_message_id,
                g.status AS game_status,
                g.name AS game_name,
                g.json_data AS game_json_data,
                gs.facilitator_message_id AS game_session_facilitator_message_id,
                gs.system_message_id AS game_session_system_message_id,
                gs.phase AS game_session_phase,
                gs.topic AS game_session_topic,
                gs.json_data AS game_session_json_data
            FROM game_session AS gs
            LEFT JOIN game AS g
            ON gs.game_id = g.id
            WHERE gs.chat_id = :chat_id
            AND gs.facilitator_message_id = :game_session_facilitator_message_id
            ORDER BY gs.system_message_id DESC
            LIMIT 1
        """
        parameters = {
            "chat_id": chat_id,
            "game_session_facilitator_message_id": game_session_facilitator_message_id,
        }
        async with self.db_connection.execute(query, parameters) as cursor:
            row = await cursor.fetchone()

            if not row:
                return None

            if row["game_id"] is None:
                game = None
            else:
                game_json_data = json.loads(row["game_json_data"])
                game_facilitator = TelegramUser.from_dict(game_json_data["facilitator"])

                game = Game.from_dict(
                    chat_id,
                    row["game_facilitator_message_id"],
                    row["game_name"],
                    game_facilitator,
                )
                game.id = row["game_id"]
                game.system_message_id = row["game_system_message_id"]
                game.status = row["game_status"]

            game_session_json_data = json.loads(row["game_session_json_data"])
            game_session_facilitator = TelegramUser.from_dict(game_session_json_data["facilitator"])

            game_session = GameSession.from_dict(
                game,
                chat_id,
                row["game_session_facilitator_message_id"],
                row["game_session_topic"],
                game_session_facilitator,
                game_session_json_data,
            )
            game_session.system_message_id = row["game_session_system_message_id"]
            game_session.phase = row["game_session_phase"]

            return game_session

    async def create_game_session(self, game_session: GameSession):
        await self.db_connection.execute(
            """
                INSERT INTO game_session
                (
                    game_id,
                    chat_id,
                    facilitator_id,
                    facilitator_message_id,
                    system_message_id,
                    phase,
                    topic,
                    json_data,
                    created_at,
                    updated_at
                ) VALUES (
                    :game_id,
                    :chat_id,
                    :facilitator_id,
                    :facilitator_message_id,
                    :system_message_id,
                    :phase,
                    :topic,
                    :json_data,
                    datetime('now'),
                    datetime('now')
                )
            """,
            {
                "game_id": game_session.game_id,
                "chat_id": game_session.chat_id,
                "facilitator_id": game_session.facilitator.id,
                "facilitator_message_id": game_session.facilitator_message_id,
                "system_message_id": game_session.system_message_id,
                "phase": game_session.phase,
                "topic": game_session.topic,
                "json_data": json.dumps(game_session.to_dict()),
            }
        )
        await self.db_connection.commit()

    async def update_game_session(self, game_session: GameSession):
        await self.db_connection.execute(
            """
                UPDATE game_session
                SET phase = :phase,
                    json_data = :json_data,
                    updated_at = datetime('now')
                WHERE chat_id = :chat_id
                AND system_message_id = :system_message_id
            """,
            {
                "phase": game_session.phase,
                "json_data": json.dumps(game_session.to_dict()),
                "chat_id": game_session.chat_id,
                "system_message_id": game_session.system_message_id,
            }
        )
        await self.db_connection.commit()

    async def get_game_statistics(self, game: Game):
        query = """
            SELECT
                COUNT(*) AS game_sessions_count,
                COUNT(DISTINCT facilitator_message_id) AS estimated_game_sessions_count
            FROM game_session
            WHERE game_id = :game_id
            AND phase = :game_session_phase
        """
        parameters = {
            "game_id": game.id,
            "game_session_phase": GameSession.PHASE_RESOLUTION,
        }
        async with self.db_connection.execute(query, parameters) as cursor:
            row = await cursor.fetchone()

            if not row:
                return None

            return {
                "game_sessions_count": row["game_sessions_count"],
                "estimated_game_sessions_count": row["estimated_game_sessions_count"],
            }