from aiotg import Bot, Chat, CallbackQuery, BotApiError
from app.utils import init_logging
from app.game import Game
from app.game_registry import GameRegistry
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
INITIATOR_OPERATIONS = [
    Game.OPERATION_START_ESTIMATION,
    Game.OPERATION_END_ESTIMATION,
    Game.OPERATION_CLEAR_VOTES,
    Game.OPERATION_RE_ESTIMATE,
]


@bot.command("/start")
@bot.command("/?help")
async def on_help_command(chat: Chat, match):
    await chat.send_text(
        GREETING,
        parse_mode="MarkdownV2",
        disable_web_page_preview=True,
    )


@bot.command("(?s)/poker\s+(.+)$")
@bot.command("/(poker)$")
async def on_poker_command(chat: Chat, match):
    topic_message_id = str(chat.message["message_id"])
    topic = match.group(1)

    if topic == "poker":
        topic = "(no topic)"

    game = Game(chat.id, topic_message_id, chat.sender, topic)
    await create_new_game_message(chat, game)


@bot.callback(r"discussion-vote-click-(.*?)-(.*?)$")
async def on_discussion_vote_click(chat: Chat, callback_query: CallbackQuery, match):
    logbook.info("{}", callback_query)
    topic_message_id = int(match.group(1))
    vote = match.group(2)
    result = "Vote `{}` accepted".format(vote)
    game = await game_registry.find_game(chat.id, topic_message_id)

    if not game:
        return await callback_query.answer(text="No such game")

    if game.phase not in Game.PHASE_DISCUSSION:
        return await callback_query.answer(text="Can't vote not in " + Game.PHASE_DISCUSSION + " phase")

    game.add_discussion_vote(callback_query.src["from"], vote)
    await game_registry.update_game(game)

    await edit_message(chat, game)

    await callback_query.answer(text=result)


@bot.callback(r"estimation-vote-click-(.*?)-(.*?)$")
async def on_estimation_vote_click(chat: Chat, callback_query: CallbackQuery, match):
    logbook.info("{}", callback_query)
    topic_message_id = int(match.group(1))
    vote = match.group(2)
    result = "Vote `{}` accepted".format(vote)
    game = await game_registry.find_game(chat.id, topic_message_id)

    if not game:
        return await callback_query.answer(text="No such game")

    if game.phase not in Game.PHASE_ESTIMATION:
        return await callback_query.answer(text="Can't vote not in " + Game.PHASE_ESTIMATION + " phase")

    game.add_estimation_vote(callback_query.src["from"], vote)
    await game_registry.update_game(game)

    await edit_message(chat, game)

    await callback_query.answer(text=result)


@bot.callback(r"({})-click-(.*?)$".format("|".join(INITIATOR_OPERATIONS)))
async def on_initiator_operation_click(chat: Chat, callback_query: CallbackQuery, match):
    operation = match.group(1)
    topic_message_id = int(match.group(2))
    game = await game_registry.find_game(chat.id, topic_message_id)

    if not game:
        return await callback_query.answer(text="No such game")

    if callback_query.src["from"]["id"] != game.initiator["id"]:
        return await callback_query.answer(text="Operation `{}` is available only for initiator".format(operation))

    if operation in Game.OPERATION_START_ESTIMATION:
        await run_operation_start_estimation(chat, game)
    elif operation in Game.OPERATION_END_ESTIMATION:
        await run_operation_end_estimation(chat, game)
    elif operation in Game.OPERATION_CLEAR_VOTES:
        await run_operation_clear_votes(chat, game)
    elif operation in Game.OPERATION_RE_ESTIMATE:
        await run_re_estimate(chat, game)
    else:
        raise Exception("Unknown operation `{}`".format(operation))

    await callback_query.answer()


async def run_operation_start_estimation(chat: Chat, game: Game):
    game.start_estimation()
    await edit_message(chat, game)
    await game_registry.update_game(game)


async def run_operation_clear_votes(chat: Chat, game: Game):
    game.clear_votes()
    await edit_message(chat, game)
    await game_registry.update_game(game)


async def run_operation_end_estimation(chat: Chat, game: Game):
    game.end_estimation()
    await edit_message(chat, game)
    await game_registry.update_game(game)


async def run_re_estimate(chat: Chat, game: Game):
    message = {
        "text": game.render_message_text(),
    }

    game.re_estimate()

    # TODO: Extract to method
    try:
        await bot.edit_message_text(chat.id, game.game_message_id, **message)
    except BotApiError:
        logbook.exception("Error when updating markup")

    await create_new_game_message(chat, game)


async def create_new_game_message(chat: Chat, game: Game):
    response = await chat.send_text(**game.get_send_kwargs())
    game.game_message_id = response["result"]["message_id"]
    await game_registry.create_game(game)


async def edit_message(chat: Chat, game: Game):
    try:
        await bot.edit_message_text(chat.id, game.game_message_id, **game.get_send_kwargs())
    except BotApiError:
        logbook.exception("Error when updating markup")


def main():
    loop = asyncio.get_event_loop()
    loop.run_until_complete(game_registry.init_db(DB_PATH))
    bot.run(reload=False)


if __name__ == "__main__":
    main()
