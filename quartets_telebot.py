import configparser

from telegram import Update, error, ParseMode
from telegram.ext import Updater, CommandHandler, CallbackContext
from quartets import Quartets, Quartets_GameState, dek_kartu, dek_baru

games = dict()
admin_id = 0


def escape_for_markdown(msg: str) -> str:
    new_msg = msg
    new_msg = new_msg.replace("-", "\-")
    new_msg = new_msg.replace("(", "\(")
    new_msg = new_msg.replace(")", "\)")
    return new_msg


def quartets_cards_msg(deck: dict, userdata: dict) -> str:
    msg = "Card data\n\n"
    for group in deck:
        if group in userdata['cards']:
            msg += f'*{group}*\n'
            for card in deck[group]:
                if card in userdata['cards'][group]:
                    msg += f'- {card} _(owned)_\n'
                else:
                    msg += f'- {card}\n'
    msg += f'\nFinished groups : {len(userdata["group_finished"])}'
    return msg


def quartets_play(user_id: int, game_id: int, **kwargs) -> list:
    msglist = list()
    # print("quartets play")
    # print("player turns", games[game_id].player_turns, "idx", games[game_id].idx_current_player_turn)
    if str(user_id) == games[game_id].player_turns[games[game_id].idx_current_player_turn]\
            or games[game_id].state in [Quartets_GameState.NOT_STARTED, Quartets_GameState.FINISHED]:
        result = games[game_id].play(**kwargs)
        # msglist.append({"type": "group", "content": f'State {games[game_id].state}'})

        if result["result"]["error"]:
            try:
                errmsg = f'Error! {result["result"]["errmsg"]}'
            except KeyError:
                errmsg = "Error!"
            msglist.append({"type": "group", "content": errmsg})

        else:
            # if games[game_id].state is Quartets_GameState.NOT_STARTED:
            #     msglist.append({"type": "group", "content": "Game not started yet"})

            if games[game_id].state is Quartets_GameState.CHOOSE_GROUP:
                msg = f'Current player: {games[game_id].player_turns[games[game_id].idx_current_player_turn]}'
                msglist.append({"type": "group", "content": msg})

                try:
                    # print("Players data")
                    # print(result["result"]["status"])
                    for player_id in result["result"]["status"]:
                        msg = f'Game ID : {game_id}\n\n'
                        msg += quartets_cards_msg(games[game_id].deck, result["result"]["status"][player_id])
                        msglist.append(
                            {"type": "private", "destination": int(player_id),
                             "content": msg})
                except KeyError:
                    pass

                msg = f'Card list sent privately\n\n'
                msg += f'Select group by using this command\n\n/ask group <group name>'
                msglist.append({"type": "group", "content": msg})

            elif games[game_id].state is Quartets_GameState.CHOOSE_PLAYER:
                msg = "Owners :\n"
                for k in result["result"]["owner"]:
                    msg += f'{k}\n'
                msg += f'\nSelect target player by using this command\n\n/ask target <owner id>'
                msglist.append({"type": "group", "content": msg})

            elif games[game_id].state is Quartets_GameState.CHOOSE_CARD:
                msg = f'Select card to ask using this command\n\n/ask cardname <card name>'
                msglist.append({"type": "group", "content": msg})

            elif games[game_id].state is Quartets_GameState.PLAYER_AGAIN:
                msg = f'You\'ve got the card! Continue!'
                msglist.append({"type": "group", "content": msg})

                try:
                    for player_id in result["result"]["status"]:
                        msg = f'Game ID : {game_id}\n\n'
                        msg += quartets_cards_msg(games[game_id].deck, result["result"]["status"][player_id])
                        msglist.append(
                            {"type": "private", "destination": int(player_id),
                             "content": msg})
                except KeyError:
                    pass

                for msg in quartets_play(user_id, game_id):
                    msglist.append(msg)

            elif games[game_id].state is Quartets_GameState.PLAYER_NEXT:
                msg = "Player switch!\n"
                msg += f'Reason: {result["result"]["msg"]}'
                msglist.append({"type": "group", "content": msg})

                for msg in quartets_play(user_id, game_id):
                    msglist.append(msg)

                msglist.append(
                    {"type": "group", "content": f'Cards left in drawing deck: {len(games[game_id].drawing_deck)}'})

            elif games[game_id].state is Quartets_GameState.FINISHED:
                msg = f'Game finished!\n\n'
                msg += f'Scores :\n'
                for player_id in result["result"]["score"]:
                    msg += f'{player_id}\t{result["result"]["score"][player_id]}\t(left {result["result"]["left"][player_id]} cards)\n'
                msglist.append({"type": "group", "content": msg})
                del games[game_id]

    else:
        msglist.append({"type": "group", "content":
            f'Not your turn! ({games[game_id].player_turns[games[game_id].idx_current_player_turn]}\'s turn)'})
    return msglist


def hi(update: Update, context: CallbackContext) -> None:
    try:
        context.bot.sendMessage(chat_id=update.effective_chat.id, text=f'Hello {update.effective_user.first_name} ({update.effective_user.id}) from {update.effective_chat.id}')
        context.bot.sendMessage(chat_id=update.effective_user.id, text=f'Hello {update.effective_user.first_name}')
    except error.Unauthorized:
        context.bot.sendMessage(chat_id=update.effective_chat.id,
                                text=f'{update.effective_user.first_name}, please chat the bot first to make sure the bot works properly')


def newgame(update: Update, context: CallbackContext) -> None:
    if update.effective_chat.id == update.effective_user.id:
        context.bot.sendMessage(chat_id=update.effective_chat.id, text=f'Game not created! Don\'t do it privately!')
    elif update.effective_chat.id not in games:
        games[update.effective_chat.id] = Quartets(dek_baru)
        context.bot.sendMessage(chat_id=update.effective_chat.id, text=f'New game created')
        join(update, context)
    else:
        context.bot.sendMessage(chat_id=update.effective_chat.id, text=f'Game exist!')
    # print("new :: Games", games)


def join(update: Update, context: CallbackContext) -> None:
    if update.effective_chat.id not in games:
        context.bot.sendMessage(chat_id=update.effective_chat.id, text=f'Create new game first!')
    else:
        if str(update.effective_user.id) in games[update.effective_chat.id].player_turns:
            context.bot.sendMessage(chat_id=update.effective_chat.id,
                                    text=f'{update.effective_user.first_name} ({update.effective_user.id}) already joined!')
        elif len(games[update.effective_chat.id].player_turns) >= len(dek_baru) - 2:
            context.bot.sendMessage(chat_id=update.effective_chat.id, text=f'Sorry, too many players!')
        else:
            try:
                context.bot.sendMessage(chat_id=update.effective_user.id,
                                        text=f'Thanks for your interest to join the game in {update.effective_chat.title} group')
            except error.Unauthorized:
                context.bot.sendMessage(chat_id=update.effective_chat.id,
                                        text=f'{update.effective_user.first_name}, please chat the bot first before joining to make sure the bot works properly')
            if games[update.effective_chat.id].add_player(str(update.effective_user.id)):
                # Send card data
                if games[update.effective_chat.id].state != Quartets_GameState.NOT_STARTED:
                    msg = f'Game ID : {update.effective_chat.id}\n\n'
                    carddata = {
                        "cards": games[update.effective_chat.id].players[str(update.effective_user.id)].cards,
                        "group_finished": games[update.effective_chat.id].players[str(update.effective_user.id)].group_finished,
                    }
                    msg += quartets_cards_msg(games[update.effective_chat.id].deck, carddata)
                    context.bot.sendMessage(chat_id=update.effective_user.id, text=escape_for_markdown(msg),
                                            parse_mode=ParseMode.MARKDOWN_V2)
                context.bot.sendMessage(chat_id=update.effective_chat.id,
                                        text=f'{update.effective_user.first_name} ({update.effective_user.id}) joined')
                msg_turns = "Player turns :\n"
                for player_id in games[update.effective_chat.id].player_turns:
                    msg_turns += f'- {player_id}\n'
                context.bot.sendMessage(chat_id=update.effective_chat.id, text=msg_turns)
            else:
                context.bot.sendMessage(chat_id=update.effective_chat.id,
                                        text=f'Sorry {update.effective_user.first_name} ({update.effective_user.id}), you can\'t join the game right now')


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
                if msg["type"] == "private":
                    context.bot.sendMessage(chat_id=msg["destination"], text=escape_for_markdown(msg["content"]),
                                            parse_mode=ParseMode.MARKDOWN_V2)
                else:
                    context.bot.sendMessage(chat_id=update.effective_chat.id, text=msg["content"])


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
                        if msg["type"] == "private":
                            context.bot.sendMessage(chat_id=msg["destination"], text=escape_for_markdown(msg["content"]),
                                                    parse_mode=ParseMode.MARKDOWN_V2)
                        else:
                            context.bot.sendMessage(chat_id=update.effective_chat.id, text=msg["content"])
                else:
                    context.bot.sendMessage(chat_id=update.effective_chat.id, text=f'Keyword error!')
            else:
                context.bot.sendMessage(chat_id=update.effective_chat.id, text=f'Incomplete command!')
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
            if msg["type"] == "private":
                context.bot.sendMessage(chat_id=msg["destination"], text=escape_for_markdown(msg["content"]),
                                        parse_mode=ParseMode.MARKDOWN_V2)
            else:
                context.bot.sendMessage(chat_id=update.effective_chat.id, text=msg["content"])


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
