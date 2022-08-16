import asyncio
import os

import logbook
from aiotg import Bot, Chat, CallbackQuery, BotApiError

from app.utils import init_logging
from app.game import GameRegistry, Game

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
"""

bot = Bot(BOT_API_TOKEN)
storage = GameRegistry()
init_logging()
INITIATOR_OPERATIONS = [
    Game.OPERATION_START,
    Game.OPERATION_RESTART,
    Game.OPERATION_END,
    Game.OPERATION_RE_VOTE,
]


@bot.command("/start")
@bot.command("/?help")
async def on_help_command(chat: Chat, match):
    await chat.send_text(
        GREETING,
        parse_mode="MarkdownV2"
    )


@bot.command("(?s)/poker\s+(.+)$")
@bot.command("/(poker)$")
async def on_start_poker_command(chat: Chat, match):
    vote_id = str(chat.message["message_id"])
    text = match.group(1)

    if text in 'poker':
        text = ''

    game = storage.new_game(chat.id, vote_id, chat.sender, text)
    resp = await chat.send_text(**game.get_send_kwargs())
    game.reply_message_id = resp["result"]["message_id"]
    await storage.save_game(game)


@bot.callback(r"ready-click-(.*?)-(.*?)$")
async def on_lobby_vote_click(chat: Chat, cq: CallbackQuery, match):
    logbook.info("{}", cq)
    vote_id = match.group(1)
    status = match.group(2)
    result = "Start status `{}` accepted".format(status)
    game = await storage.get_game(chat.id, vote_id)

    if not game:
        return await cq.answer(text="No such game")

    if game.phase not in Game.PHASE_INITIATING:
        return await cq.answer(text="Can't change ready status not in initiating phase")

    game.add_lobby_vote(cq.src["from"], status)
    await storage.save_game(game)

    await edit_message(chat, game)

    await cq.answer(text=result)


@bot.callback(r"vote-click-(.*?)-(.*?)$")
async def on_vote_click(chat: Chat, cq: CallbackQuery, match):
    logbook.info("{}", cq)
    vote_id = match.group(1)
    point = match.group(2)
    result = "Answer `{}` accepted".format(point)
    game = await storage.get_game(chat.id, vote_id)

    if not game:
        return await cq.answer(text="No such game")

    if game.phase not in Game.PHASE_VOTING:
        return await cq.answer(text="Can't change vote not in voting phase")

    game.add_vote(cq.src["from"], point)
    await storage.save_game(game)

    await edit_message(chat, game)

    await cq.answer(text=result)


@bot.callback(r"({})-click-(.*?)$".format("|".join(INITIATOR_OPERATIONS)))
async def on_initiator_operation_click(chat: Chat, cq: CallbackQuery, match):
    operation = match.group(1)
    vote_id = match.group(2)
    game = await storage.get_game(chat.id, vote_id)

    if not game:
        return await cq.answer(text="No such game")

    if cq.src["from"]["id"] != game.initiator["id"]:
        return await cq.answer(text="Operation '{}' is available only for initiator".format(operation))

    if operation in Game.OPERATION_START:
        await run_operation_start(chat, game)
    elif operation in Game.OPERATION_RESTART:
        await run_operation_restart(chat, game)
    elif operation in Game.OPERATION_END:
        await run_operation_end(chat, game)
    elif operation in Game.OPERATION_RE_VOTE:
        # TODO: Extract to method
        original_message_text = game.render()

        game.re_vote()

        message = {
            "text": original_message_text,
        }

        try:
            await bot.edit_message_text(chat.id, game.reply_message_id, **message)
        except BotApiError:
            logbook.exception("Error when updating markup")

        response = await chat.send_text(**game.get_send_kwargs())
        game.reply_message_id = response["result"]["message_id"]
    else:
        raise Exception("Unknown operation `{}`".format(operation))

    await storage.save_game(game)
    await cq.answer()


async def run_operation_start(chat: Chat, game: Game):
    game.start()
    await edit_message(chat, game)


async def run_operation_restart(chat: Chat, game: Game):
    game.restart()
    await edit_message(chat, game)


async def run_operation_end(chat: Chat, game: Game):
    game.end()
    await edit_message(chat, game)


async def edit_message(chat: Chat, game: Game):
    try:
        # TODO: Extract to method
        await bot.edit_message_text(chat.id, game.reply_message_id, **game.get_send_kwargs())
    except BotApiError:
        logbook.exception("Error when updating markup")


def main():
    loop = asyncio.get_event_loop()
    loop.run_until_complete(storage.init_db(DB_PATH))
    bot.run(reload=False)


if __name__ == '__main__':
    main()
