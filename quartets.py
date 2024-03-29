import enum
import random


class QuartetsGameState(enum.Enum):
    NOT_STARTED = enum.auto()
    CHOOSE_GROUP = enum.auto()
    CHOOSE_PLAYER = enum.auto()
    CHOOSE_CARD = enum.auto()
    PLAYER_AGAIN = enum.auto()
    PLAYER_NEXT = enum.auto()
    FINISHED = enum.auto()


class QuartetsPlayer(object):
    def __init__(self):
        self.cards = dict()
        self.group_finished = list()

    def cards_left(self) -> int:
        left = 0
        for group in self.cards:
            left += len(self.cards[group])
        return left

    def card_check_complete(self) -> None:
        for group in self.cards:
            if len(self.cards[group]) == 4:
                self.group_finished.append(group)
        for group in self.group_finished:
            try:
                del self.cards[group]
                # print("group + " group cards complete")
            except KeyError:
                pass

    def card_take(self, card: dict) -> None:
        try:
            self.cards[card["group"]].append(card["name"])
        except:
            self.cards[card["group"]] = [card["name"]]
        self.card_check_complete()

    def card_give(self, card: dict) -> bool:
        if self.have_card(card):
            self.cards[card["group"]].remove(card["name"])
            if len(self.cards[card["group"]]) == 0:
                del self.cards[card["group"]]
            return True
        return False

    def list_group(self) -> list:
        group = list()
        while not group:
            for _group in self.cards:
                group.append(_group)
        return group

    def list_cards(self, category: str) -> list:
        return self.cards[category]

    def have_group(self, group: str) -> bool:
        return True if group in self.cards else False

    def have_card(self, card: dict) -> bool:
        if self.have_group(card["group"]):
            return True if card["name"] in self.cards[card["group"]] else False
        return False


class Quartets(object):
    def __init__(self, deck: dict):
        self.deck = deck
        self.players = dict()
        self.player_turns = list()
        self.drawing_deck = list()
        self.idx_current_player_turn = 0
        self.id_player_target = -1
        self.current_category = str()
        self.state = QuartetsGameState.NOT_STARTED
        for group in deck:
            for cardname in deck[group]:
                self.drawing_deck.append({"group": group, "name": cardname})

    def add_player(self, player_id: str) -> bool:
        if (self.state == QuartetsGameState.NOT_STARTED) and (len(self.players) < len(self.deck) - 2):
            self.players[player_id] = QuartetsPlayer()
            self.player_turns.append(player_id)
            return True
        # At least 4 cards remaining after new player joined
        elif (self.state != QuartetsGameState.NOT_STARTED) and (len(self.drawing_deck) >= (4 + 4)):
            self.players[player_id] = QuartetsPlayer()
            self.player_turns.append(player_id)
            for i in range(0, 4):
                self.draw(self.players[player_id])
            return True
        else:
            return False

    def remove_player(self, player_id: str) -> bool:
        if len(self.players) > 2 or self.state == QuartetsGameState.NOT_STARTED:
            for group in self.players[player_id].cards:
                for cardname in self.players[player_id].cards:
                    self.drawing_deck.append({"group": group, "name": cardname})
            self.player_turns.remove(player_id)
            del self.players[player_id]
            if self.idx_current_player_turn >= len(self.players):
                self.idx_current_player_turn = 0
            return True
        else:
            return False

    def current_player_id(self) -> str:
        return self.player_turns[self.idx_current_player_turn]

    def current_player(self) -> QuartetsPlayer:
        return self.players[self.current_player_id()]

    def player_status(self, player_id: str) -> dict:
        data = dict()
        try:
            data = {
                "cards": self.players[player_id].cards,
                "group_finished": self.players[player_id].group_finished,
            }
        except KeyError:
            pass
        return data

    def draw(self, player: QuartetsPlayer) -> None:
        card = self.drawing_deck[random.randint(0, len(self.drawing_deck) - 1)]
        player.card_take(card)
        self.drawing_deck.remove(card)

    def first_draw(self):
        for player_id in self.players:
            for i in range(0, 4):
                self.draw(self.players[player_id])

    def start_play(self):
        self.first_draw()
        for player_id in self.players:
            self.players[player_id].card_check_complete()
            if not self.players[player_id].cards_left():
                self.draw(self.players[player_id])

    def play(self, **kwargs) -> dict:
        data = dict()
        data["result"] = {"error": True, "status": dict()}

        # if not len(self.drawing_deck):
        #     self.state = Quartets_GameState.FINISHED

        if self.state == QuartetsGameState.NOT_STARTED:
            self.start_play()
            self.idx_current_player_turn = 0
            # print(f'Current player : {self.player_turns[self.idx_current_player_turn]}')
            for player_id in self.player_turns:
                data["result"]["status"][player_id] = self.player_status(player_id)
            data["result"]["error"] = False
            self.state = QuartetsGameState.CHOOSE_GROUP

        if self.state == QuartetsGameState.PLAYER_AGAIN:
            data["result"]["error"] = False
            self.state = QuartetsGameState.CHOOSE_GROUP

        if self.state == QuartetsGameState.PLAYER_NEXT:
            self.draw(self.current_player())
            data["result"]["status"][self.current_player_id()] = self.player_status(self.current_player_id())

            self.idx_current_player_turn += 1
            if self.idx_current_player_turn >= len(self.players):
                self.idx_current_player_turn = 0
            # print(f'Switch player to {self.player_turns[self.idx_current_player_turn]}')
            data["result"]["error"] = False
            if not len(self.drawing_deck):
                self.state = QuartetsGameState.FINISHED
            else:
                self.state = QuartetsGameState.CHOOSE_GROUP

        if self.state == QuartetsGameState.CHOOSE_GROUP:
            try:
                if kwargs["group"] in self.current_player().list_group():
                    self.current_category = kwargs["group"]
                    self.state = QuartetsGameState.CHOOSE_PLAYER
                    data["result"]["error"] = False
                else:
                    raise KeyError
            except KeyError:
                data["result"]["group"] = self.current_player().list_group()
                if data["result"]["error"]:
                    data["result"]["errmsg"] = "Invalid group chosen!"

        if self.state == QuartetsGameState.CHOOSE_PLAYER:
            data["result"]["owner"] = list()
            data["result"]["owner"] = self.check_group_owners(self.current_category)
            data["result"]["owner"].remove(self.current_player_id())
            if not data["result"]["owner"]:
                self.state = QuartetsGameState.PLAYER_NEXT
                data["result"]["msg"] = "No one have any cards belong to the group!"
            else:
                try:
                    if kwargs["target"] in data["result"]["owner"]:
                        self.id_player_target = kwargs["target"]
                        self.state = QuartetsGameState.CHOOSE_CARD
                        data["result"]["error"] = False
                    else:
                        raise KeyError
                except KeyError:
                    if data["result"]["error"]:
                        data["result"]["errmsg"] = "Invalid target player!"

        if self.state == QuartetsGameState.CHOOSE_CARD:
            data["result"]["cards"] = dict()
            data["result"]["cards"] = {
                "list": self.deck[self.current_category],
                "owned": self.current_player().list_cards(self.current_category),
            }
            try:
                if kwargs["cardname"] in self.deck[self.current_category]:
                    if self.players[self.id_player_target].have_card(
                            {'group': self.current_category, 'name': kwargs["cardname"]}):
                        self.players[self.id_player_target].card_give(
                            {'group': self.current_category, 'name': kwargs["cardname"]}
                        )
                        self.current_player().card_take(
                            {'group': self.current_category, 'name': kwargs["cardname"]}
                        )

                        # Pemain (lain) tidak memiliki kartu di tangan
                        if not len(self.players[self.id_player_target].cards) and len(self.drawing_deck):
                            self.draw(self.players[self.id_player_target])

                        # print("add target card data")
                        data["result"]["status"][self.id_player_target] = self.player_status(self.id_player_target)
                        # print(data["result"]["status"])

                        data["result"]["received"] = True
                        if not len(self.drawing_deck):
                            self.state = QuartetsGameState.FINISHED
                        else:
                            self.state = QuartetsGameState.PLAYER_AGAIN
                    else:
                        self.state = QuartetsGameState.PLAYER_NEXT
                        data["result"]["msg"] = "Wrong card!"
                    data["result"]["error"] = False
                else:
                    raise KeyError
            except KeyError:
                if data["result"]["error"]:
                    data["result"]["errmsg"] = "Invalid card name!"

        self.players[self.player_turns[self.idx_current_player_turn]].card_check_complete()
        if not len(self.current_player().cards) and len(self.drawing_deck):
            self.draw(self.current_player())
            if not len(self.drawing_deck):
                self.state = QuartetsGameState.FINISHED

        if self.state == QuartetsGameState.FINISHED:
            data["result"]["score"] = dict()
            data["result"]["left"] = dict()
            for player_id in self.players:
                data["result"]["score"][player_id] = len(self.players[player_id].group_finished)
                data["result"]["left"][player_id] = self.players[player_id].cards_left()
            data["result"]["error"] = False

        data["current_player"] = self.current_player_id()
        data["result"]["status"][self.current_player_id()] = self.player_status(self.current_player_id())
        # print(data["result"]["status"])

        return data

    def check_group_owners(self, group: str) -> list:
        owners = list()
        for player_id in self.players:
            if self.players[player_id].have_group(group):
                owners.append(player_id)
        return owners
