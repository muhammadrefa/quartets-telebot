import configparser

from string import Template
from telegram import Update, error, ParseMode, Bot
from telegram.ext import Updater, CommandHandler, CallbackContext
from quartets import Quartets, Quartets_GameState, dek_kartu, dek_baru
from quartets_msgobj import QuartetsMessage, QuartetsCardList

games = dict()
admin_id = 0


def change_game_placeholder(bot: Bot, msg: Template, gamedata: dict) -> str:
    data = dict()
    for key in gamedata:
        if gamedata[key] not in data:
            data[gamedata[key]] = bot.getChat(gamedata[key])
        if "GROUPNAME" in key:
            gamedata[key] = data[gamedata[key]].title
        elif "USERNAME" in key:
            gamedata[key] = data[gamedata[key]].username
        elif "NAME" in key:
            gamedata[key] = data[gamedata[key]].full_name
    return msg.safe_substitute(gamedata)


def quartets_play(user_id: int, game_id: int, **kwargs) -> list:
    # TODO : Generate template
    msglist = list()
    # print("quartets play")
    # print("player turns", games[game_id].player_turns, "idx", games[game_id].idx_current_player_turn)
    if str(user_id) == games[game_id].player_turns[games[game_id].idx_current_player_turn]\
            or games[game_id].state in [Quartets_GameState.NOT_STARTED, Quartets_GameState.FINISHED]:
        result = games[game_id].play(**kwargs)

        if result["result"]["error"]:
            msg = QuartetsMessage()
            msg.destination = game_id
            try:
                msg.set_message(f'Error! {result["result"]["errmsg"]}')
            except KeyError:
                msg.set_message("Error!")
            msglist.append(msg)

        else:
            # if games[game_id].state is Quartets_GameState.NOT_STARTED:
            #     msglist.append({"type": "group", "content": "Game not started yet"})

            if games[game_id].state is Quartets_GameState.CHOOSE_GROUP:
                player_id = games[game_id].player_turns[games[game_id].idx_current_player_turn]
                msg = QuartetsMessage()
                msg.destination = game_id
                msg.set_template(f'Current player: $NAME1 (@$USERNAME1 {player_id})')
                msglist.append(msg)

                try:
                    # print("Players data")
                    # print(result["result"]["status"])
                    msg = QuartetsCardList.generate_message(
                        games[game_id].deck,
                        result["result"]["status"],
                        game_id=game_id
                    )
                    msglist += msg
                except KeyError:
                    pass

                msg = QuartetsMessage()
                msg.destination = game_id
                msg.set_message(
                    "Card list sent privately\n\n"
                    "Select group by using this command\n\n"
                    "/ask group <group name>"
                )
                msglist.append(msg)

            elif games[game_id].state is Quartets_GameState.CHOOSE_PLAYER:
                gamedata = dict()
                _msg = "Owners :\n"
                for i, k in enumerate(result["result"]["owner"]):
                    _msg += f'$NAME{str(i)} ($USERNAME{str(i)} {k})\n'
                    gamedata["NAME" + str(i)] = k
                    gamedata["USERNAME" + str(i)] = k
                _msg += f'\nSelect target player by using this command\n\n/ask target <owner id>'
                msg = QuartetsMessage()
                msg.destination = game_id
                msg.set_template(_msg)
                msglist.append(msg)

            elif games[game_id].state is Quartets_GameState.CHOOSE_CARD:
                msg = QuartetsMessage()
                msg.destination = game_id
                msg.set_message(f'Select card to ask using this command\n\n/ask cardname <card name>')
                msglist.append(msg)

            elif games[game_id].state is Quartets_GameState.PLAYER_AGAIN:
                msg = QuartetsMessage()
                msg.destination = game_id
                msg.set_message(f'You\'ve got the card! Continue!')
                msglist.append(msg)

                try:
                    msg = QuartetsCardList.generate_message(
                        games[game_id].deck,
                        result["result"]["status"],
                        game_id=game_id
                    )
                    msglist += msg
                except KeyError:
                    pass

                msglist += quartets_play(user_id, game_id)

            elif games[game_id].state is Quartets_GameState.PLAYER_NEXT:
                msg = QuartetsMessage()
                msg.destination = game_id
                msg.set_message(
                    "Player switch!\n"
                    f'Reason: {result["result"]["msg"]}'
                )
                msglist.append(msg)

                new_msglist = quartets_play(user_id, game_id)

                msg = QuartetsMessage()
                msg.destination = game_id
                msg.set_message(f'Cards left in drawing deck: {len(games[game_id].drawing_deck)}')
                msglist.append(msg)

                msglist += new_msglist

            elif games[game_id].state is Quartets_GameState.FINISHED:
                _msg = f'Game finished!\n\n'
                _msg += f'Scores :\n'
                for player_id in result["result"]["score"]:
                    _msg += f'{player_id}\t{result["result"]["score"][player_id]}\t(left {result["result"]["left"][player_id]} cards)\n'
                del games[game_id]
                msg = QuartetsMessage()
                msg.destination = game_id
                msg.set_message(_msg)

    else:
        player_id = games[game_id].player_turns[games[game_id].idx_current_player_turn]
        msg = QuartetsMessage()
        msg.destination = game_id
        msg.set_template(f'Not your turn! ($NAME\'s turn) (User ID {player_id})')
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
        games[update.effective_chat.id] = Quartets(dek_baru)
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
        if str(update.effective_user.id) in games[update.effective_chat.id].player_turns:
            context.bot.sendMessage(
                chat_id=update.effective_chat.id,
                reply_to_message_id=update.message.message_id,
                text=f'{update.effective_user.first_name} ({update.effective_user.id}) already joined!'
            )
        elif len(games[update.effective_chat.id].player_turns) >= len(dek_baru) - 2:
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

                if games[update.effective_chat.id].add_player(str(update.effective_user.id)):
                    # Send card data
                    if games[update.effective_chat.id].state != Quartets_GameState.NOT_STARTED:
                        carddata = dict()
                        carddata[str(update.effective_user.id)] = {
                            "cards": games[update.effective_chat.id].players[str(update.effective_user.id)].cards,
                            "group_finished": games[update.effective_chat.id].players[
                                str(update.effective_user.id)].group_finished,
                        }
                        msg = QuartetsCardList.generate_message(games[update.effective_chat.id].deck, carddata, game_id=update.effective_chat.id)
                        context.bot.sendMessage(
                            chat_id=update.effective_user.id,
                            text=msg[0].message,
                            parse_mode=ParseMode.HTML
                        )
                    context.bot.sendMessage(
                        chat_id=update.effective_chat.id,
                        reply_to_message_id=update.message.message_id,
                        text=f'{update.effective_user.first_name} ({update.effective_user.id}) joined'
                    )
                    msg_turns = "Player turns :\n"
                    turns_data = dict()
                    for i, player_id in enumerate(games[update.effective_chat.id].player_turns):
                        msg_turns += f'- $NAME{str(i)} ($USERNAME{str(i)} {player_id})\n'
                        turns_data["NAME" + str(i)] = player_id
                        turns_data["USERNAME" + str(i)] = player_id
                    context.bot.sendMessage(
                        chat_id=update.effective_chat.id,
                        text=change_game_placeholder(context.bot, Template(msg_turns), turns_data)
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
        if str(update.effective_user.id) in games[update.effective_chat.id].players:
            if games[update.effective_chat.id].remove_player(str(update.effective_user.id)):
                context.bot.sendMessage(chat_id=update.effective_chat.id,
                                        text=f'{update.effective_user.first_name} ({update.effective_user.id}) not joining the game anymore')
            else:
                context.bot.sendMessage(chat_id=update.effective_chat.id,
                                        text=f'{update.effective_user.first_name} ({update.effective_user.id}) can\'t unjoin the game!')
        else:
            context.bot.sendMessage(chat_id=update.effective_chat.id,
                                    text=f'{update.effective_user.first_name} ({update.effective_user.id}) not joining the game!')
        msg_turns = "Player turns :\n"
        for player_id in games[update.effective_chat.id].player_turns:
            msg_turns += f'- {player_id}\n'
        context.bot.sendMessage(chat_id=update.effective_chat.id, text=msg_turns)


def startgame(update: Update, context: CallbackContext) -> None:
    # print("start :: Games", games)
    if update.effective_chat.id not in games:
        context.bot.sendMessage(chat_id=update.effective_chat.id, text=f'Create new game first!')
    else:
        if len(games[update.effective_chat.id].players) < 2:
            context.bot.sendMessage(chat_id=update.effective_chat.id, text=f'Need at least 2 players to start!')
        else:
            context.bot.sendMessage(chat_id=update.effective_chat.id,
                                    text=f'Game started ({update.effective_chat.id})')
            msglists = quartets_play(update.effective_user.id, update.effective_chat.id)
            for msg in msglists:
                if not msg.message:
                    msg.generate_message({})
                print("msg", msg.message)
                context.bot.sendMessage(
                    chat_id=msg.destination,
                    text=msg.message,
                    parse_mode=ParseMode.HTML
                )


def ask(update: Update, context: CallbackContext) -> None:
    if update.effective_chat.id not in games:
        context.bot.sendMessage(chat_id=update.effective_chat.id, text=f'Create new game first!')
    else:
        try:
            cmd = update.message.text.split(" ", 2)
            kwartet_kwargs = dict()
            if len(cmd) > 2:
                keywords = ["group", "target", "cardname"]
                if cmd[1].lower() in keywords:
                    kwartet_kwargs[cmd[1].lower()] = cmd[2]
                    msglists = quartets_play(update.effective_user.id, update.effective_chat.id, **kwartet_kwargs)
                    for msg in msglists:
                        if not msg.message:
                            msg.generate_message({})
                        context.bot.sendMessage(
                            chat_id=msg.destination,
                            text=msg.message,
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


def endgame(update: Update, context: CallbackContext) -> None:
    # print("end :: Games", games)
    if update.effective_chat.id not in games:
        context.bot.sendMessage(chat_id=update.effective_chat.id, text=f'No game existed!')
    else:
        context.bot.sendMessage(chat_id=update.effective_chat.id, text=f'Ending game...')
        games[update.effective_chat.id].state = Quartets_GameState.FINISHED
        msglists = quartets_play(update.effective_user.id, update.effective_chat.id)
        for msg in msglists:
            if not msg.message:
                msg.generate_message({})
            context.bot.sendMessage(
                chat_id=msg.destination,
                text=msg.message,
                parse_mode=ParseMode.HTML
            )


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

    admin_id = int(telebot_cfg["telebot"]["admin"])
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

    updater.start_polling()
    updater.idle()
