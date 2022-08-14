# Telegram DevPoker Bot

Planning Poker (Scrum Poker) for Agile software development teams.
The bot allows you to introduce a consensus-based, gamified technique of task estimating into Telegram group chats.

![devpoker-hero-image](https://user-images.githubusercontent.com/1849174/184529872-aa0f8235-90d5-4a75-85df-5a63b73dbe02.gif)

## Usage

> ⚠️ Work in progress. Public bot may be offline until the first stable release.

Add [@devpoker_bot](https://t.me/devpoker_bot?startgroup=true) to the group chat.

To start **Planning Poker** use `/poker` command.
Add any description after the command to provide context. 

Example:
```
/poker Design DevPoker Bot keyboard layout
``` 

Example with multiline description:
```
/poker Design DevPoker bot keyboard layout
https://issue\.tracker/TASK-123
```

Only initiator can open cards or restart game at any moment. 

Currently, there is only one sequence of numbers:
```
0, 0.5, 1, 2, 3, 4
5, 6, 7, 8, 9, 10
12, 18, 24, 30
```

Special cases:
* ✂️ — Task must be broken down
* ♾️ — Impossible to estimate or task cannot be completed
* ❓— Unsure how to estimate
* ☕ — I need a break

## Self-hosted usage

Bot works on Python 3.6.

Run `run.sh` script with bot api token to start the Docker container.

You need to obtain own bot token from https://t.me/BotFather, then run:

```shell
DEVPOKER_BOT_API_TOKEN=11111424242:some-token ./run.sh
```

This command will create image and container `devpoker-bot`.

Bot uses SQLite database at host in `~/.devpoker_bot/devpoker_bot.db`.

## Credits

This project is highly inspired by the [tg-planning-poker](https://github.com/reclosedev/tg-planning-poker).

## License

- `Telegram DevPoker Bot` is open-sourced software licensed under the [MIT license](LICENSE) by [Anton Komarev].

## About CyberCog

[CyberCog] is a Social Unity of enthusiasts.
Research the best solutions in product & software development is our passion.

- [Follow us on Twitter](https://twitter.com/cybercog)

<a href="https://cybercog.su"><img src="https://cloud.githubusercontent.com/assets/1849174/18418932/e9edb390-7860-11e6-8a43-aa3fad524664.png" alt="CyberCog"></a>

[Anton Komarev]: https://komarev.com
[CyberCog]: https://cybercog.su
