import configparser

from string import Template
from telegram import Update, error, ParseMode, Bot
from telegram.ext import Updater, CommandHandler, CallbackContext
from quartets import Quartets, Quartets_GameState, dek_kartu, dek_baru
from quartets_msgobj import QuartetsMessage, QuartetsCardList

games = dict()
admin_id = None


class QuartetsTelebotGame(object):
    def __init__(self, deck):
        self.game = Quartets(deck)
        self.group_data = dict()
        self.player_data = dict()

    def join(self, player_data: dict) -> bool:
        try:
            if player_data["id"] in self.player_data:
                return False
            self.player_data[str(player_data["id"])] = {
                "name": player_data["name"],
                "username": player_data["username"]
            }
            if self.game.add_player(str(player_data["id"])):
                return True
            else:
                del self.player_data[str(player_data["id"])]
                return False
        except KeyError:
            return False

    def unjoin(self, player_id: str) -> bool:
        if player_id not in self.player_data:
            return False
        if len(self.player_turns()) < 2:
            return False
        if self.game.remove_player(player_id):
            del self.player_data[player_id]
            return True
        else:
            return False

    def player_turns(self) -> list:
        turns = list()
        for player_id in self.game.player_turns:
            player_data = self.player_data[player_id]
            player_data["id"] = player_id
            turns.append(player_data)
        return turns

    def play(self, user_id: int, **kwargs) -> list:
        msglist = list()
        # print("quartets play")
        if str(user_id) == str(self.game.current_player_id())\
                or self.game.state in [Quartets_GameState.NOT_STARTED, Quartets_GameState.FINISHED]:
            result = self.game.play(**kwargs)

            if result["result"]["error"]:
                msg = QuartetsMessage()
                msg.destination = self.group_data["id"]
                try:
                    msg.set_message(f'Error! {result["result"]["errmsg"]}')
                except KeyError:
                    msg.set_message("Error!")
                msglist.append(msg)

            else:
                # if games[game_id]["game"].state is Quartets_GameState.NOT_STARTED:
                #     msglist.append({"type": "group", "content": "Game not started yet"})

                if self.game.state is Quartets_GameState.CHOOSE_GROUP:
                    player_id = self.game.current_player_id()
                    msg = QuartetsMessage()
                    msg.destination = self.group_data["id"]
                    msg.set_template(f'Current player: $NAME (@$USERNAME $ID)')
                    msg.generate_message(
                        {
                            "NAME": self.player_data[player_id]["name"],
                            "USERNAME": self.player_data[player_id]["username"] if self.player_data[player_id]["username"] is not None else "",
                            "ID": player_id
                        }
                    )
                    msglist.append(msg)

                    try:
                        # print("Players data")
                        # print(result["result"]["status"])
                        msg = QuartetsCardList.generate_message(
                            self.game.deck,
                            result["result"]["status"],
                            gamedata={"group": self.group_data, "players": self.player_data}
                        )
                        msglist += msg
                    except KeyError:
                        pass

                    msg = QuartetsMessage()
                    msg.destination = self.group_data["id"]
                    msg.set_message(
                        "Card list sent privately\n\n"
                        "Select group by using this command\n\n"
                        "/ask group <group name>"
                    )
                    msglist.append(msg)

                elif self.game.state is Quartets_GameState.CHOOSE_PLAYER:
                    _msg = "Owners :\n"
                    for i, k in enumerate(result["result"]["owner"]):
                        if self.player_data[k]["username"] is not None:
                            _msg += f'- {self.player_data[k]["name"]} ({self.player_data[k]["username"]} {k})\n'
                        else:
                            _msg += f'- {self.player_data[k]["name"]} ({k})\n'
                    _msg += f'\nSelect target player by using this command\n\n' \
                            f'/ask target <owner id>\n' \
                            f'or\n' \
                            f'/ask target <username>'
                    msg = QuartetsMessage()
                    msg.destination = self.group_data["id"]
                    msg.set_template(_msg)
                    msglist.append(msg)

                elif self.game.state is Quartets_GameState.CHOOSE_CARD:
                    msg = QuartetsMessage()
                    msg.destination = self.group_data["id"]
                    msg.set_message(f'Select card to ask using this command\n\n/ask cardname <card name>')
                    msglist.append(msg)

                elif self.game.state is Quartets_GameState.PLAYER_AGAIN:
                    msg = QuartetsMessage()
                    msg.destination = self.group_data["id"]
                    msg.set_message(f'You\'ve got the card! Continue!')
                    msglist.append(msg)

                    try:
                        msg = QuartetsCardList.generate_message(
                            self.game.deck,
                            result["result"]["status"],
                            gamedata={"group": self.group_data, "players": self.player_data}
                        )
                        msglist += msg
                    except KeyError:
                        pass

                    msglist += self.play(user_id)

                elif self.game.state is Quartets_GameState.PLAYER_NEXT:
                    msg = QuartetsMessage()
                    msg.destination = self.group_data["id"]
                    msg.set_message(
                        "Player switch!\n"
                        f'Reason: {result["result"]["msg"]}'
                    )
                    msglist.append(msg)

                    new_msglist = self.play(user_id)

                    msg = QuartetsMessage()
                    msg.destination = self.group_data["id"]
                    msg.set_message(f'Cards left in drawing deck: {len(self.game.drawing_deck)}')
                    msglist.append(msg)

                    msglist += new_msglist

                elif self.game.state is Quartets_GameState.FINISHED:
                    _msgdata = dict()
                    _msg = f'Game finished!\n\n'
                    _msg += f'Scores :\n'
                    for i, player_id in enumerate(result["result"]["score"]):
                        _msg += f'$NAME{str(i)} ($USERID{str(i)})\t$SCORE{str(i)}\t(left $LEFT{str(i)} cards)\n'
                        _msgdata["NAME" + str(i)] = self.player_data[player_id]["name"]
                        _msgdata["USERID" + str(i)] = player_id
                        _msgdata["SCORE" + str(i)] = result["result"]["score"][player_id]
                        _msgdata["LEFT" + str(i)] = result["result"]["left"][player_id]
                    msg = QuartetsMessage()
                    msg.destination = self.group_data["id"]
                    msg.set_template(_msg)
                    msg.generate_message(_msgdata)
                    msglist.append(msg)

        else:
            player_id = self.game.current_player_id()
            msg = QuartetsMessage()
            msg.destination = self.group_data["id"]
            msg.set_template(f'Not your turn! ($NAME\'s turn) (User ID $ID)')
            msg.generate_message(
                {
                    "NAME": self.player_data[player_id]["name"],
                    "USERNAME": self.player_data[player_id]["username"] if not None else "",
                    "ID": player_id
                }
            )
            msglist.append(msg)
        return msglist


def hi(update: Update, context: CallbackContext) -> None:
    try:
        context.bot.sendMessage(
            chat_id=update.effective_chat.id,
            text=f'Hello {update.effective_user.first_name} ({update.effective_user.id}) from {update.effective_chat.id}'
        )
        context.bot.sendMessage(
            chat_id=update.effective_user.id,
            text=f'Hello {update.effective_user.first_name}'
        )
    except error.Unauthorized:
        context.bot.sendMessage(
            chat_id=update.effective_chat.id,
            text=f'{update.effective_user.first_name}, please chat the bot first to make sure the bot works properly'
        )


def newgame(update: Update, context: CallbackContext) -> None:
    if update.effective_chat.id == update.effective_user.id:
        context.bot.sendMessage(
            chat_id=update.effective_chat.id,
            reply_to_message_id=update.message.message_id,
            text=f'Game not created! Don\'t do it privately!'
        )
    elif update.effective_chat.id not in games:
        games[update.effective_chat.id] = QuartetsTelebotGame(dek_baru)
        games[update.effective_chat.id].group_data = {
            "id": update.effective_chat.id,
            "name": update.effective_chat.title
        }
        context.bot.sendMessage(
            chat_id=update.effective_chat.id,
            reply_to_message_id=update.message.message_id,
            text=f'New game created'
        )
        join(update, context)
    else:
        context.bot.sendMessage(
            chat_id=update.effective_chat.id,
            reply_to_message_id=update.message.message_id,
            text=f'Game exist!'
        )
    # print("new :: Games", games)


def join(update: Update, context: CallbackContext) -> None:
    if update.effective_chat.id not in games:
        context.bot.sendMessage(chat_id=update.effective_chat.id, text=f'Create new game first!')
    else:
        if str(update.effective_user.id) in games[update.effective_chat.id].game.player_turns:
            context.bot.sendMessage(
                chat_id=update.effective_chat.id,
                reply_to_message_id=update.message.message_id,
                text=f'{update.effective_user.first_name} ({update.effective_user.id}) already joined!'
            )
        elif len(games[update.effective_chat.id].game.player_turns) >= len(dek_baru) - 2:
            context.bot.sendMessage(
                chat_id=update.effective_chat.id,
                reply_to_message_id=update.message.message_id,
                text=f'Sorry, too many players!'
            )
        else:
            try:
                context.bot.sendMessage(
                    chat_id=update.effective_user.id,
                    text=f'Thanks for your interest to join the game in {update.effective_chat.title} group'
                )

                if games[update.effective_chat.id].join(
                        {
                            "id": update.effective_user.id,
                            "name": update.effective_user.full_name,
                            "username": update.effective_user.username
                        }
                ):
                    # Send card data
                    if games[update.effective_chat.id].game.state != Quartets_GameState.NOT_STARTED:
                        carddata = games[update.effective_chat.id].game.player_status(str(update.effective_user.id))
                        msg = QuartetsCardList.generate_message(
                            games[update.effective_chat.id].game.deck,
                            carddata,
                            gamedata=games[update.effective_chat.id]
                        )
                        context.bot.sendMessage(
                            chat_id=msg[0].destination,
                            text=msg[0].get_message(),
                            parse_mode=ParseMode.HTML
                        )
                    context.bot.sendMessage(
                        chat_id=update.effective_chat.id,
                        reply_to_message_id=update.message.message_id,
                        text=f'{update.effective_user.first_name} ({update.effective_user.id}) joined'
                    )

                    msg_turns = "Player turns :\n"
                    for player_data in games[update.effective_chat.id].player_turns():
                        msg_turns += f'- {player_data["name"]} ({player_data["username"]} {player_data["id"]})\n'
                    msg = QuartetsMessage()
                    msg.destination = update.effective_chat.id
                    msg.set_message(msg_turns)
                    context.bot.sendMessage(
                        chat_id=msg.destination,
                        text=msg.get_message(),
                        parse_mode=ParseMode.HTML
                    )
                else:
                    context.bot.sendMessage(
                        chat_id=update.effective_chat.id,
                        reply_to_message_id=update.message.message_id,
                        text=f'Sorry {update.effective_user.first_name} ({update.effective_user.id}), you can\'t join the game right now'
                    )
            except error.Unauthorized:
                context.bot.sendMessage(
                    chat_id=update.effective_chat.id,
                    reply_to_message_id=update.message.message_id,
                    text=f'{update.effective_user.first_name}, please chat the bot first before joining to make sure the bot works properly'
                )


def unjoin(update: Update, context: CallbackContext) -> None:
    if update.effective_chat.id not in games:
        context.bot.sendMessage(chat_id=update.effective_chat.id, text=f'Create new game first!')
    else:
        if str(update.effective_user.id) in games[update.effective_chat.id].player_turns:
            if games[update.effective_chat.id].unjoin:
                context.bot.sendMessage(
                    chat_id=update.effective_chat.id,
                    reply_to_message_id=update.message.message_id,
                    text=f'{update.effective_user.first_name} ({update.effective_user.id}) not joining the game anymore'
                )
            else:
                context.bot.sendMessage(
                    chat_id=update.effective_chat.id,
                    reply_to_message_id=update.message.message_id,
                    text=f'{update.effective_user.first_name} ({update.effective_user.id}) can\'t unjoin the game!'
                )
        else:
            context.bot.sendMessage(
                chat_id=update.effective_chat.id,
                reply_to_message_id=update.message.message_id,
                text=f'{update.effective_user.first_name} ({update.effective_user.id}) not joining the game!'
            )

        msg_turns = "Player turns :\n"
        for player_data in games[update.effective_chat.id].player_turns():
            msg_turns += f'- {player_data["name"]} ({player_data["username"]} {player_data["id"]})\n'
        msg = QuartetsMessage()
        msg.destination = update.effective_chat.id
        msg.set_message(msg_turns)
        context.bot.sendMessage(
            chat_id=msg.destination,
            text=msg.get_message(),
            parse_mode=ParseMode.HTML
        )


def startgame(update: Update, context: CallbackContext) -> None:
    # print("start :: Games", games)
    if update.effective_chat.id not in games:
        context.bot.sendMessage(chat_id=update.effective_chat.id, text=f'Create new game first!')
    else:
        if len(games[update.effective_chat.id].game.players) < 2:
            context.bot.sendMessage(chat_id=update.effective_chat.id, text=f'Need at least 2 players to start!')
        else:
            context.bot.sendMessage(chat_id=update.effective_chat.id,
                                    text=f'Game started ({update.effective_chat.id})')
            msglists = games[update.effective_chat.id].play(update.effective_user.id)
            for msg in msglists:
                context.bot.sendMessage(
                    chat_id=msg.destination,
                    text=msg.get_message(),
                    parse_mode=ParseMode.HTML
                )


def ask(update: Update, context: CallbackContext) -> None:
    if update.effective_chat.id not in games:
        context.bot.sendMessage(chat_id=update.effective_chat.id, text=f'Create new game first!')
    else:
        try:
            cmd = update.message.text.split(" ", 2)
            quartets_kwargs = dict()
            if len(cmd) > 2:
                keywords = ["group", "target", "cardname"]
                if cmd[1].lower() in keywords:
                    if cmd[1].lower() == "target":
                        # Convert usernames to user id
                        if cmd[2] not in games[update.effective_chat.id].player_data:
                            if cmd[2][0] == "@":
                                cmd[2] = cmd[2][1:]
                            # Iterate all players
                            for player_id in games[update.effective_chat.id].player_data:
                                if games[update.effective_chat.id].player_data[player_id]["username"] == cmd[2]:
                                    cmd[2] = player_id
                                    break
                    quartets_kwargs[cmd[1].lower()] = cmd[2]
                    msglists = games[update.effective_chat.id].play(update.effective_user.id, **quartets_kwargs)
                    for msg in msglists:
                        context.bot.sendMessage(
                            chat_id=msg.destination,
                            text=msg.get_message(),
                            parse_mode=ParseMode.HTML
                        )
                else:
                    context.bot.sendMessage(
                        chat_id=update.effective_chat.id,
                        reply_to_message_id=update.message.message_id,
                        text=f'Keyword error!'
                    )
            else:
                context.bot.sendMessage(
                    chat_id=update.effective_chat.id,
                    reply_to_message_id=update.message.message_id,
                    text=f'Incomplete command!'
                )
        except AttributeError:  # Edited message
            pass
    if games[update.effective_chat.id].game.state == Quartets_GameState.FINISHED:
        del games[update.effective_chat.id]


def endgame(update: Update, context: CallbackContext) -> None:
    # print("end :: Games", games)
    if update.effective_chat.id not in games:
        context.bot.sendMessage(chat_id=update.effective_chat.id, text=f'No game existed!')
    else:
        context.bot.sendMessage(chat_id=update.effective_chat.id, text=f'Ending game...')
        games[update.effective_chat.id].game.state = Quartets_GameState.FINISHED
        msglists = games[update.effective_chat.id].play(update.effective_user.id)
        for msg in msglists:
            context.bot.sendMessage(
                chat_id=msg.destination,
                text=msg.get_message(),
                parse_mode=ParseMode.HTML
            )
        del games[update.effective_chat.id]


def rules(update: Update, context: CallbackContext) -> None:
    msg_rules = "Game rules :\n" \
                "- The purpose of the game is to complete as many groups as you can\n" \
                "- Players will be sent card list via private message (make sure you ever send message privately to the bot first)\n" \
                "- Current player select a group to ask based on current player's card groups\n" \
                "- If any player (except current) have any cards that belong to the group, current player will choose a player to be it's target\n" \
                "- Current player sends the card name to ask\n" \
                "- If the target player has the card, the current player will get it, and continue it's turn\n" \
                "- If the target player doesn't have the card, the current player will take a card from drawing deck, and continue to next player\n" \
                "- Game will end if no cards left in the drawing deck\n" \
                "- Winner based on how many groups complete"
    context.bot.sendMessage(chat_id=update.effective_chat.id, text=msg_rules)


def help(update: Update, context: CallbackContext) -> None:
    msg = f'Commands recognized :\n' \
          f'/hi\tSend introduction message\n' \
          f'/newgame\tCreate new quartets game\n' \
          f'/join\tJoin to existing quartets game\n' \
          f'/unjoin\tUnjoin to quartets game\n' \
          f'/startgame\tStart quartets game\n' \
          f'/ask\tDepend on context\n' \
          f'/endgame\tStop game\n' \
          f'/rules\tGame rules\n' \
          f'/help\tShow help (this message)'
    context.bot.sendMessage(chat_id=update.effective_chat.id, text=msg)


def admin(update: Update, context: CallbackContext) -> None:
    if admin_id is not None:
        if update.effective_chat.id == admin_id:
            cmd = update.message.text.split(" ", 2)
            if len(cmd) > 1:
                if cmd[1] == "gamelists":
                    context.bot.sendMessage(chat_id=update.effective_chat.id, text=str(list(games)))
                elif cmd[1] == "deletegame":
                    try:
                        del games[int(cmd[2])]
                        context.bot.sendMessage(chat_id=update.effective_chat.id, text=f'Game ID {cmd[2]} deleted')
                    except IndexError:
                        context.bot.sendMessage(chat_id=update.effective_chat.id, text="Send the game ID")
                    except KeyError:
                        context.bot.sendMessage(chat_id=update.effective_chat.id, text=f'Wrong Game ID!')
            else:
                context.bot.sendMessage(chat_id=update.effective_chat.id, text="Yes, you are admin")


if __name__ == "__main__":
    telebot_cfg = configparser.ConfigParser()
    telebot_cfg.read("telebot.cfg")

    try:
        admin_id = int(telebot_cfg["telebot"]["admin"])
    except ValueError:
        admin_id = None
    updater = Updater(telebot_cfg["telebot"]["token"])

    updater.dispatcher.add_handler(CommandHandler('hi', hi))
    updater.dispatcher.add_handler(CommandHandler('newgame', newgame))
    updater.dispatcher.add_handler(CommandHandler('join', join))
    updater.dispatcher.add_handler(CommandHandler('unjoin', unjoin))
    updater.dispatcher.add_handler(CommandHandler('startgame', startgame))
    updater.dispatcher.add_handler(CommandHandler('ask', ask))
    updater.dispatcher.add_handler(CommandHandler('endgame', endgame))
    updater.dispatcher.add_handler(CommandHandler('rules', rules))
    updater.dispatcher.add_handler(CommandHandler('help', help))
    updater.dispatcher.add_handler(CommandHandler('admin', admin))

    updater.start_polling(drop_pending_updates=True)
    updater.idle()
