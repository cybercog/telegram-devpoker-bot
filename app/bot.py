from aiotg import Bot, Chat, CallbackQuery, BotApiError
from app.utils import init_logging
from app.telegram_user import TelegramUser
from app.game import Game
from app.game_registry import GameRegistry
from app.game_session import GameSession
import asyncio
import logbook
import os

BOT_API_TOKEN = os.environ["DEVPOKER_BOT_API_TOKEN"]
DB_PATH = os.environ["DEVPOKER_BOT_DB_PATH"]

GREETING = """
To start *Planning Poker* use /poker command\.
Add any description after the command to provide context\.

*Example:*
```
/poker https://issue\.tracker/TASK-123
```

*Example with multiline description:*
```
/poker https://issue\.tracker/TASK-123
Design DevPoker bot keyboard layout
```

Currently, there is only one sequence of numbers from 0 to 30\.

Special cases:
\* ✂️ — Task must be broken down
\* ♾️ — Impossible to estimate or task cannot be completed
\* ❓— Unsure how to estimate
\* ☕ — I need a break

[Discussions on GitHub](https://github.com/cybercog/telegram-devpoker-bot/discussions)
"""

bot = Bot(BOT_API_TOKEN)
game_registry = GameRegistry()
init_logging()
FACILITATOR_OPERATIONS = [
    GameSession.OPERATION_START_ESTIMATION,
    GameSession.OPERATION_END_ESTIMATION,
    GameSession.OPERATION_CLEAR_VOTES,
    GameSession.OPERATION_RE_ESTIMATE,
]


@bot.command("/start")
@bot.command("/?help")
async def on_help_command(chat: Chat, match):
    await chat.send_text(
        GREETING,
        parse_mode="MarkdownV2",
        disable_web_page_preview=True,
    )


@bot.command("(?s)/game\s+(.+)$")
@bot.command("/(game)$")
async def on_game_command(chat: Chat, match):
    chat_id = chat.id
    facilitator_message_id = str(chat.message["message_id"])
    game_name = match.group(1)
    facilitator = TelegramUser.from_dict(chat.sender)

    if game_name == "game":
        game_name = "(no name)"

    active_game = await game_registry.find_active_game(chat_id, facilitator)
    if active_game is not None:
        await chat.send_text(
            text="You have active game already. Need to /game_end to start another one."
        )
        return

    game = Game(chat_id, facilitator_message_id, game_name, facilitator)
    await create_game(chat, game)


@bot.command("/game_end$")
async def on_game_end_command(chat: Chat, match):
    chat_id = chat.id
    facilitator = TelegramUser.from_dict(chat.sender)

    active_game = await game_registry.find_active_game(chat_id, facilitator)

    if active_game is None:
        await chat.send_text(
            text="You do not have active game. Need to run /game to start game."
        )
        return

    await end_game(chat, active_game)


@bot.command("(?s)/poker\s+(.+)$")
@bot.command("/(poker)$")
async def on_poker_command(chat: Chat, match):
    chat_id = chat.id
    facilitator_message_id = str(chat.message["message_id"])
    topic = match.group(1)
    facilitator = TelegramUser.from_dict(chat.sender)

    if topic == "poker":
        topic = "(no topic)"

    game = await game_registry.find_active_game(chat_id, facilitator)

    game_session = GameSession(game, chat_id, facilitator_message_id, topic, facilitator)
    await create_game_session(chat, game_session)


@bot.callback(r"discussion-vote-click-(.*?)-(.*?)$")
async def on_discussion_vote_click(chat: Chat, callback_query: CallbackQuery, match):
    logbook.info("{}", callback_query)
    facilitator_message_id = int(match.group(1))
    vote = match.group(2)
    result = "Vote `{}` accepted".format(vote)
    game_session = await game_registry.find_active_game_session(chat.id, facilitator_message_id)

    if not game_session:
        return await callback_query.answer(text="No such game session")

    if game_session.phase not in GameSession.PHASE_DISCUSSION:
        return await callback_query.answer(text="Can't vote not in " + GameSession.PHASE_DISCUSSION + " phase")

    game_session.add_discussion_vote(callback_query.src["from"], vote)
    await game_registry.update_game_session(game_session)

    await edit_message(chat, game_session)

    await callback_query.answer(text=result)


@bot.callback(r"estimation-vote-click-(.*?)-(.*?)$")
async def on_estimation_vote_click(chat: Chat, callback_query: CallbackQuery, match):
    logbook.info("{}", callback_query)
    chat_id = chat.id
    facilitator_message_id = int(match.group(1))
    vote = match.group(2)
    result = "Vote `{}` accepted".format(vote)
    game_session = await game_registry.find_active_game_session(chat_id, facilitator_message_id)

    if not game_session:
        return await callback_query.answer(text="No such game session")

    if game_session.phase not in GameSession.PHASE_ESTIMATION:
        return await callback_query.answer(text="Can't vote not in " + GameSession.PHASE_ESTIMATION + " phase")

    game_session.add_estimation_vote(callback_query.src["from"], vote)
    await game_registry.update_game_session(game_session)

    await edit_message(chat, game_session)

    await callback_query.answer(text=result)


@bot.callback(r"({})-click-(.*?)$".format("|".join(FACILITATOR_OPERATIONS)))
async def on_facilitator_operation_click(chat: Chat, callback_query: CallbackQuery, match):
    operation = match.group(1)
    chat_id = chat.id
    facilitator_message_id = int(match.group(2))
    game_session = await game_registry.find_active_game_session(chat_id, facilitator_message_id)

    if not game_session:
        return await callback_query.answer(text="No such game session")

    if callback_query.src["from"]["id"] != game_session.facilitator.id:
        return await callback_query.answer(text="Operation `{}` is available only for facilitator".format(operation))

    if operation in GameSession.OPERATION_START_ESTIMATION:
        await run_operation_start_estimation(chat, game_session)
    elif operation in GameSession.OPERATION_END_ESTIMATION:
        await run_operation_end_estimation(chat, game_session)
    elif operation in GameSession.OPERATION_CLEAR_VOTES:
        await run_operation_clear_votes(chat, game_session)
    elif operation in GameSession.OPERATION_RE_ESTIMATE:
        await run_re_estimate(chat, game_session)
    else:
        raise Exception("Unknown operation `{}`".format(operation))

    await callback_query.answer()


async def run_operation_start_estimation(chat: Chat, game_session: GameSession):
    game_session.start_estimation()
    await edit_message(chat, game_session)
    await game_registry.update_game_session(game_session)


async def run_operation_clear_votes(chat: Chat, game_session: GameSession):
    game_session.clear_votes()
    await edit_message(chat, game_session)
    await game_registry.update_game_session(game_session)


async def run_operation_end_estimation(chat: Chat, game_session: GameSession):
    game_session.end_estimation()
    await edit_message(chat, game_session)
    await game_registry.update_game_session(game_session)


async def run_re_estimate(chat: Chat, game_session: GameSession):
    message = {
        "text": game_session.render_system_message_text(),
    }

    game_session.re_estimate()

    # TODO: Extract to method
    try:
        await bot.edit_message_text(chat.id, game_session.system_message_id, **message)
    except BotApiError:
        logbook.exception("Error when updating markup")

    await create_game_session(chat, game_session)


async def create_game(chat: Chat, game_prototype: Game):
    response = await chat.send_text(**game_prototype.render_system_message())
    game_prototype.system_message_id = response["result"]["message_id"]
    await game_registry.create_game(game_prototype)


async def end_game(chat: Chat, game: Game):
    game.end()
    await game_registry.update_game(game)
    game_statistics = await game_registry.get_game_statistics(game)
    await chat.send_text(**game.render_results_system_message(game_statistics))


async def create_game_session(chat: Chat, game_session_prototype: GameSession):
    response = await chat.send_text(**game_session_prototype.render_system_message())
    game_session_prototype.system_message_id = response["result"]["message_id"]
    await game_registry.create_game_session(game_session_prototype)


async def edit_message(chat: Chat, game_session: GameSession):
    try:
        await bot.edit_message_text(chat.id, game_session.system_message_id, **game_session.render_system_message())
    except BotApiError:
        logbook.exception("Error when updating markup")


def main():
    loop = asyncio.get_event_loop()
    loop.run_until_complete(game_registry.init_db(DB_PATH))
    bot.run(reload=False)


if __name__ == "__main__":
    main()
