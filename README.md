# Quartets Telegram Bot
Telegram bot that allows you to play quartets card game

## What is Quartets Card Game?
Quartets card game is a game where the players need to collect as many groups (consists of 4 cards) as it can
to win the game.

Every player starts with 4 cards, asking for card to each other, and give the card if the guessing
is correct, or draw the card when the guessing is incorrect (or not having any cards in hand).

The game ends when there is no cards left in the drawing deck.

## How to run the bot?
To run the bot, you need :
- Bot Token (get it from [@BotFather](http://telegram.me/BotFather))
- Python 3 (tested using version 3.6)
- [Python Telegram Bot](https://github.com/python-telegram-bot/python-telegram-bot) module (tested using version 13.5)

Configure the bot by editing `telebot.cfg` file
- `token` : Bot Token
- `admin` : Admin User ID (optional to run admin commands)

Run the bot using `python3 quartets_telebot.py` inside the project folder
