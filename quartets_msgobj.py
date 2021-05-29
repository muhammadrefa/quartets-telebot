from string import Template
from quartets import Quartets
from telegram import Bot


class QuartetsMessage(object):
    def __init__(self):
        self.destination = None
        self.reply_to = None
        self.message = str()
        self.template = None
        self.is_html = False

    def set_message(self, message: str, is_html: bool = False):
        self.is_html = is_html
        self.message = message

    def set_template(self, template: str):
        self.template = Template(template)

    def generate_message(self, template_data: dict):
        self.message = self.template.safe_substitute(template_data)
        return self.message

    def get_message(self):
        message = self.message
        if not message:
            message = self.generate_message({})
        if not self.is_html:
            message = self.escape_html(message)
        return message

    @staticmethod
    def escape_html(msg: str):
        new_msg = msg
        new_msg = new_msg.replace("&", "&amp;")
        new_msg = new_msg.replace("<", "&lt;")
        new_msg = new_msg.replace(">", "&gt;")
        new_msg = new_msg.replace("\"", "&quot;")
        return new_msg


class QuartetsCardList(object):
    def __init__(self):
        pass

    @staticmethod
    def generate_message(deck: dict, player_status: dict, gamedata: dict = None) -> list:
        msglist = list()
        for player_id in player_status:
            _msg = str()
            msg = QuartetsMessage()
            msg.destination = player_id

            if gamedata is not None:
                header = f'Game ID: {gamedata["group"]["id"]}\nGroup: {gamedata["group"]["name"]}\n\n'
                _msg += QuartetsMessage.escape_html(header)
            _msg += "Card data\n\n"
            for group in deck:
                if group in player_status[player_id]['cards']:
                    _msg += f'<b>{group}</b>\n'
                    for card in deck[group]:
                        if card in player_status[player_id]['cards'][group]:
                            _msg += f'- {card} <i>(owned)</i>\n'
                        else:
                            _msg += f'- {card}\n'
            _msg += f'\nFinished groups : {len(player_status[player_id]["group_finished"])}'
            msg.set_template(_msg)
            msg.is_html = True
            msglist.append(msg)
        return msglist
