import enum
import random

from typing import Dict, List


class QuartetsGameState(enum.Enum):
    NOT_STARTED = enum.auto()
    CHOOSE_GROUP = enum.auto()
    CHOOSE_PLAYER = enum.auto()
    CHOOSE_CARD = enum.auto()
    PLAYER_AGAIN = enum.auto()
    PLAYER_NEXT = enum.auto()
    FINISHED = enum.auto()


class QuartetsCard(object):
    def __init__(self, group, name):
        self._group = group
        self._name = name

    @property
    def group(self) -> str:
        return self._group

    @property
    def name(self) -> str:
        return self._name


class QuartetsDeck(object):
    def __init__(self, card_collections: Dict[str, str]):
        self._deck: List[QuartetsCard] = list()
        self._drawed: List[QuartetsCard] = list()
        self._available_group: List[str] = list()
        for group in card_collections:
            if len(card_collections[group]) == 4:
                self._available_group.append(group)
                for cardname in card_collections[group]:
                    self._deck.append(QuartetsCard(group, cardname))

    @property
    def cardpack_groups(self) -> List[str]:
        return self._available_group

    @property
    def number_of_groups(self) -> int:
        return len(self._available_group)

    @property
    def cards_remaining(self) -> int:
        return len(self._deck)

    def get_cards(self, group: str = None) -> List[QuartetsCard]:
        cards = list()
        for card in (self._deck + self._drawed):
            if (group is None) or (card.group == group):
                cards.append(card)
        return cards

    def draw(self) -> QuartetsCard:
        card = self._deck.pop(random.randint(0, len(self._deck)))
        self._drawed.append(card)
        return card

    def add_to_deck(self, card: QuartetsCard):
        self._deck.append(card)


class QuartetsPlayer(object):
    def __init__(self):
        self._cards_in_hand: Dict[str, List[QuartetsCard]] = dict()
        self._group_finished: List[str] = list()

    @property
    def cards_in_hand(self) -> List[QuartetsCard]:
        cards = list()
        for group in self._cards_in_hand:
            for card in self._cards_in_hand[group]:
                cards.append(card)
        return cards

    @property
    def group_finished(self) -> list:
        return self._group_finished

    def list_group(self) -> list:
        return [group for group in self._cards_in_hand]

    def list_cards(self, category: str) -> list:
        return self._cards_in_hand[category]

    def have_group(self, group: str) -> bool:
        return True if group in self._cards_in_hand else False

    def have_card(self, card: QuartetsCard) -> bool:
        if self.have_group(card.group):
            return True if card in self._cards_in_hand[card.group] else False
        return False

    def _check_completeness(self) -> None:
        for group in self._cards_in_hand:
            if len(self._cards_in_hand[group]) == 4:
                self._group_finished.append(group)
        for group in self._group_finished:
            try:
                del self._cards_in_hand[group]
                # print("group + " group cards complete")
            except KeyError:
                pass

    def receive_card(self, card: QuartetsCard) -> None:
        try:
            self._cards_in_hand[card.group].append(card)
        except KeyError:
            self._cards_in_hand[card.group] = list()
            self._cards_in_hand[card.group].append(card)
        self._check_completeness()

    def remove_card(self, card: QuartetsCard) -> bool:
        if self.have_card(card):
            self._cards_in_hand[card.group].remove(card)
            if len(self._cards_in_hand[card.group]) == 0:
                del self._cards_in_hand[card.group]
            return True
        return False


class Quartets(object):
    def __init__(self, deck: Dict[str, str]):
        self.deck: QuartetsDeck = QuartetsDeck(deck)
        self.players: Dict[str, QuartetsPlayer] = dict()
        self.player_turns = list()
        self.idx_current_player_turn = 0
        self.id_player_target = -1
        self.current_category = str()
        self.state = QuartetsGameState.NOT_STARTED
        self._max_player: int = self.deck.number_of_groups - 2

    @property
    def current_player_id(self) -> str:
        return self.player_turns[self.idx_current_player_turn]

    @property
    def current_player(self) -> QuartetsPlayer:
        return self.players[self.current_player_id]

    def next_player(self) -> None:
        self.idx_current_player_turn += 1
        if self.idx_current_player_turn >= len(self.players):
            self.idx_current_player_turn = 0

    def add_player(self, player_id: str) -> bool:
        if self.possible_to_add_more_player():
            self.players[player_id] = QuartetsPlayer()
            self.player_turns.append(player_id)

            if self.state != QuartetsGameState.NOT_STARTED:
                for i in range(0, 4):
                    self.draw(self.players[player_id])

            return True
        return False

    def possible_to_add_more_player(self) -> bool:
        # Make sure the game held for at least for 2 rounds
        cards_remaining = 0
        if self.state == QuartetsGameState.NOT_STARTED:
            cards_will_be_handed = (len(self.players) + 1) * 4
            cards_remaining = self.deck.cards_remaining - cards_will_be_handed
        else:
            cards_remaining = self.deck.cards_remaining

        if cards_remaining >= (len(self.players) * 2):
            return True
        else:
            return False

    def remove_player(self, player_id: str) -> bool:
        if len(self.players) >= 3 or self.state == QuartetsGameState.NOT_STARTED:
            for card in self.players[player_id].cards_in_hand:
                self.deck.add_to_deck(card)
            self.player_turns.remove(player_id)
            del self.players[player_id]
            if self.idx_current_player_turn >= len(self.players):
                self.idx_current_player_turn = 0
            return True
        return False

    def player_status(self, player_id: str) -> dict:
        data = dict()
        try:
            data = {
                "cards": self.players[player_id].cards_in_hand,
                "group_finished": self.players[player_id].group_finished,
            }
        except KeyError:
            pass
        return data

    def draw(self, player: QuartetsPlayer) -> None:
        if self.deck.cards_remaining:
            card = self.deck.draw()
            player.receive_card(card)
            if len(player.cards_in_hand) == 0:
                self.draw(player)

    def first_draw(self):
        for player_id in self.players:
            for i in range(0, 4):
                self.draw(self.players[player_id])

    def start_play(self):
        self.first_draw()

    def get_state_data(self) -> dict:
        data = dict()

        if self.state == QuartetsGameState.CHOOSE_GROUP:
            data["current_player"] = self.current_player_id
            data[self.current_player_id] = self.player_status(self.current_player_id)
            data["groups"] = self.current_player.list_group()

        elif self.state == QuartetsGameState.CHOOSE_PLAYER:
            data["owner"] = list()
            data["owner"] = self.check_group_owners(self.current_category)
            data["owner"].remove(self.current_player_id)

        elif self.state == QuartetsGameState.CHOOSE_CARD:
            data["cards"] = dict()
            data["cards"] = {
                "list": self.deck.get_cards(self.current_category),
                "owned": self.current_player.list_cards(self.current_category),
            }

        elif self.state == QuartetsGameState.PLAYER_AGAIN:
            pass

        elif self.state == QuartetsGameState.PLAYER_NEXT:
            self.draw(self.current_player)
            self.next_player()

        return data

    def play(self, **kwargs) -> dict:
        data = dict()
        data["result"] = {"error": True, "data": dict()}

        # Result:
        # {
        #   "error": boolean (true/false),
        #   "errmsg": str,
        #   "msg": str,
        #   "data": {
        #       "current_player": player id
        #       <player_id>: {
        #           "cards": [cards in hand],
        #           "group_finished": [group finished]
        #       },
        #       <other player id if any>: {},
        #   }
        # }

        # if not len(self.drawing_deck):
        #     self.state = Quartets_GameState.FINISHED

        # Switch state
        if self.state == QuartetsGameState.NOT_STARTED:
            self.start_play()
            self.idx_current_player_turn = 0
            for player_id in self.player_turns:
                data["result"]["status"][player_id] = self.player_status(player_id)
            data["result"]["error"] = False
            self.state = QuartetsGameState.CHOOSE_GROUP

        elif self.state == QuartetsGameState.CHOOSE_GROUP:
            try:
                if kwargs["group"] in self.current_player.list_group():
                    self.current_category = kwargs["group"]
                    if self.check_group_owners(self.current_category):
                        self.state = QuartetsGameState.CHOOSE_PLAYER
                    else:
                        self.state = QuartetsGameState.PLAYER_NEXT
                        data["msg"] = "No one have any cards belong to the group!"
                    data["result"]["error"] = False
                else:
                    raise KeyError
            except KeyError:
                data["result"]["status"][self.current_player_id] = self.player_status(self.current_player_id)
                if data["result"]["error"]:
                    data["result"]["errmsg"] = "Invalid group chosen!"

        elif self.state == QuartetsGameState.CHOOSE_PLAYER:
            try:
                if kwargs["target"] in self.check_group_owners(self.current_category):
                    self.id_player_target = kwargs["target"]
                    self.state = QuartetsGameState.CHOOSE_CARD
                    data["result"]["error"] = False
                else:
                    raise KeyError
            except KeyError:
                if data["result"]["error"]:
                    data["result"]["errmsg"] = "Invalid target player!"

        elif self.state == QuartetsGameState.CHOOSE_CARD:
            if self.player_ask_for_card(
                    self.current_player,
                    self.players[self.id_player_target],
                    QuartetsCard(self.current_category, kwargs["cardname"])
            ):
                self.state = QuartetsGameState.PLAYER_AGAIN
            else:
                self.state = QuartetsGameState.PLAYER_NEXT

        self.get_state_data()

        # TODO: Do something if no cards in the deck

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
                if kwargs["group"] in self.current_player.list_group():
                    self.current_category = kwargs["group"]
                    self.state = QuartetsGameState.CHOOSE_PLAYER
                    data["result"]["error"] = False
                else:
                    raise KeyError
            except KeyError:
                data["result"]["group"] = self.current_player.list_group()
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
                "owned": self.current_player.list_cards(self.current_category),
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
                        if not len(self.players[self.id_player_target]._cards) and len(self.drawing_deck):
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
        if not len(self.current_player()._cards_in_hand) and len(self.drawing_deck):
            self.draw(self.current_player())
            if not len(self.drawing_deck):
                self.state = QuartetsGameState.FINISHED

        if self.state == QuartetsGameState.FINISHED:
            data["result"]["score"] = dict()
            data["result"]["left"] = dict()
            for player_id in self.players:
                data["result"]["score"][player_id] = len(self.players[player_id]._group_finished)
                data["result"]["left"][player_id] = self.players[player_id].cards_left_cnt()
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

    def player_ask_for_card(self,
                            player_asking: QuartetsPlayer,
                            player_target: QuartetsPlayer,
                            card: QuartetsCard) -> bool:
        if player_target.have_card(card):
            player_target.remove_card(card)
            player_asking.receive_card(card)

            # Check if target player does not have any cards left
            if len(player_target.cards_in_hand) == 0:
                self.draw(player_target)
            return True
        return False
