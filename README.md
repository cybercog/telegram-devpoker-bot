# Developers Planning Poker Bot for Telegram

This bot allows software development teams to play Planning Poker game in the Telegram group chats.

![](https://user-images.githubusercontent.com/1849174/184502550-3469c04d-e99b-4709-9159-081f3c9aaa3d.png)

## Usage

Add https://t.me/devpoker_bot to group chat.

To start **Planning Poker** use `/poker` command.
Add any description after the command to provide context. 

Example:
```
/poker Redesign Planning Poker Bot keyboard layout
``` 

Example with multiline description:
```
/poker Redesign planning poker bot keyboard layout
https://issue\.tracker/TASK-123
```

Only initiator can open cards or restart game at any moment. 

Currently, there is only one scale of numbers:
```
0, 0.5, 1, 2, 3, 4
5, 6, 7, 8, 9, 10
12, 18, 24, 30
```

Additional votes:
* ❓— Still unsure how to estimate
* ∞ — Task is too large, impossible to estimate
* ☕ — Let's take a break

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

- `Telegram Dev Planning Poker Bot` is open-sourced software licensed under the [MIT license](LICENSE) by [Anton Komarev].

## About CyberCog

[CyberCog] is a Social Unity of enthusiasts.
Research the best solutions in product & software development is our passion.

- [Follow us on Twitter](https://twitter.com/cybercog)

<a href="https://cybercog.su"><img src="https://cloud.githubusercontent.com/assets/1849174/18418932/e9edb390-7860-11e6-8a43-aa3fad524664.png" alt="CyberCog"></a>

[Anton Komarev]: https://komarev.com
[CyberCog]: https://cybercog.su
