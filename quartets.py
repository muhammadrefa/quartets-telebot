import enum
import random


class Quartets_GameState(enum.Enum):
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
        self.state = Quartets_GameState.NOT_STARTED
        for group in deck:
            for cardname in deck[group]:
                self.drawing_deck.append({"group": group, "name": cardname})

    def add_player(self, player_id: str) -> bool:
        if (self.state == Quartets_GameState.NOT_STARTED) and (len(self.players) < len(self.deck) - 2):
            self.players[player_id] = QuartetsPlayer()
            self.player_turns.append(player_id)
            return True
        elif len(self.drawing_deck) >= (4 + 4):  # At least 4 cards remaining after new player joined
            self.players[player_id] = QuartetsPlayer()
            self.player_turns.append(player_id)
            for i in range(0, 4):
                self.draw(self.players[player_id])
            return True
        else:
            return False

    def remove_player(self, player_id: str) -> bool:
        if len(self.players) > 2 or self.state == Quartets_GameState.NOT_STARTED:
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

        if not len(self.drawing_deck):
            self.state = Quartets_GameState.FINISHED

        if self.state == Quartets_GameState.NOT_STARTED:
            self.start_play()
            self.idx_current_player_turn = 0
            # print(f'Current player : {self.player_turns[self.idx_current_player_turn]}')
            for player_id in self.player_turns:
                data["result"]["status"][player_id] = self.player_status(player_id)
            data["result"]["error"] = False
            self.state = Quartets_GameState.CHOOSE_GROUP

        if self.state == Quartets_GameState.PLAYER_AGAIN:
            data["result"]["error"] = False
            self.state = Quartets_GameState.CHOOSE_GROUP

        if self.state == Quartets_GameState.PLAYER_NEXT:
            self.draw(self.current_player())
            data["result"]["status"][self.current_player_id()] = self.player_status(self.current_player_id())

            self.idx_current_player_turn += 1
            if self.idx_current_player_turn >= len(self.players):
                self.idx_current_player_turn = 0
            # print(f'Switch player to {self.player_turns[self.idx_current_player_turn]}')
            data["result"]["error"] = False
            self.state = Quartets_GameState.CHOOSE_GROUP

        if self.state == Quartets_GameState.CHOOSE_GROUP:
            try:
                if kwargs["group"] in self.current_player().list_group():
                    self.current_category = kwargs["group"]
                    self.state = Quartets_GameState.CHOOSE_PLAYER
                    data["result"]["error"] = False
                else:
                    raise KeyError
            except KeyError:
                data["result"]["group"] = self.current_player().list_group()
                if data["result"]["error"]:
                    data["result"]["errmsg"] = "Invalid group chosen!"

        if self.state == Quartets_GameState.CHOOSE_PLAYER:
            data["result"]["owner"] = list()
            data["result"]["owner"] = self.check_group_owners(self.current_category)
            data["result"]["owner"].remove(self.current_player_id())
            if not data["result"]["owner"]:
                self.state = Quartets_GameState.PLAYER_NEXT
                data["result"]["msg"] = "No one have any cards belong to the group!"
            else:
                try:
                    if kwargs["target"] in data["result"]["owner"]:
                        self.id_player_target = kwargs["target"]
                        self.state = Quartets_GameState.CHOOSE_CARD
                        data["result"]["error"] = False
                    else:
                        raise KeyError
                except KeyError:
                    if data["result"]["error"]:
                        data["result"]["errmsg"] = "Invalid target player!"

        if self.state == Quartets_GameState.CHOOSE_CARD:
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
                        self.state = Quartets_GameState.PLAYER_AGAIN
                    else:
                        self.state = Quartets_GameState.PLAYER_NEXT
                        data["result"]["msg"] = "Wrong card!"
                    data["result"]["error"] = False
            except KeyError:
                if data["result"]["error"]:
                    data["result"]["errmsg"] = "Invalid card name!"

        if self.state == Quartets_GameState.FINISHED:
            data["result"]["score"] = dict()
            data["result"]["left"] = dict()
            for player_id in self.players:
                data["result"]["score"][player_id] = len(self.players[player_id].group_finished)
                data["result"]["left"][player_id] = self.players[player_id].cards_left()
            data["result"]["error"] = False

        self.players[self.player_turns[self.idx_current_player_turn]].card_check_complete()
        if not len(self.current_player().cards) and len(self.drawing_deck):
            self.draw(self.current_player())

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

    def play_prompt(self):
        self.start_play()

        while len(self.drawing_deck):
            print("players total :", len(self.players))
            for player_id in self.players:
                continue_play = True
                while continue_play:
                    if len(self.drawing_deck):
                        print("Current player (" + player_id + ")")

                        group_owned = self.players[player_id].list_group()
                        print("Groups :")
                        for k in group_owned:
                            print(k)
                        group_asked = str()
                        while group_asked not in group_owned:
                            group_asked = input("Pilih kategori: ")

                        card_owners = list()
                        for other_player_id in self.players:
                            if other_player_id == player_id:
                                continue
                            if self.players[other_player_id].have_group(group_asked):
                                card_owners.append(other_player_id)

                        if card_owners:
                            print("Owners :", card_owners)
                            target_id = str()
                            while target_id not in card_owners:
                                target_id = input("Target : ")

                            cards_owned = self.players[player_id].list_cards(group_asked)
                            print("Cards :")
                            for k in self.deck[group_asked]:
                                if k in cards_owned:
                                    print(k + " (owned)")
                                else:
                                    print(k)

                            card_asked = str()
                            while card_asked not in self.deck[group_asked]:
                                card_asked = input("Select card to take: ")

                            if self.players[target_id].have_card({'group': group_asked, 'name': card_asked}):
                                print("Card received!")
                                self.players[target_id].card_give({
                                    'group': group_asked,
                                    'name': card_asked
                                })
                                self.players[player_id].card_take({'group': group_asked, 'name': card_asked})
                                # Other player doesn't have card remaining
                                if not len(self.players[target_id].cards) and len(self.drawing_deck):
                                    self.draw(self.players[player_id])

                            else:
                                print("Wrong card!")
                                self.draw(self.players[player_id])
                                continue_play = False

                        else:
                            print("No one have any cards belong to the group!")
                            self.draw(self.players[player_id])
                            continue_play = False

                        self.players[player_id].card_check_complete()

                        if not len(self.players[player_id].cards) and len(self.drawing_deck):
                            self.draw(self.players[player_id])
                    else:
                        break

        print("Game finished!")
        print("Score :")
        for player_id in self.players:
            print(player_id + '\t' + str(len(self.players[player_id].group_finished)))


dek_kartu = {
    "kategori 1": ["kartuA", "kartuB", "kartuC", "kartuD"],
    "kategori 2": ["kartuE", "kartuF", "kartuG", "kartuH"],
    "kategori 3": ["kartuI", "kartuJ", "kartuK", "kartuL"],
    # "kategori 4": ["kartuM", "kartuN", "kartuO", "kartuP"],
    # "kategori 5": ["kartuQ", "kartuR", "kartuS", "kartuT"],
}

dek_baru = {
    "nasi": ["nasi goreng", "nasi uduk", "nasi kuning", "nasi kucing"],
    "air": ["air putih", "air santan", "air susu", "air tajin"],
    "benda lengkung": ["busur", "karet", "tampah", "jembatan"],
    "minuman": ["kopi", "teh", "cincau", "boba"],
    "sumber tenaga": ["listrik", "bensin", "matahari", "karbohidrat"],
    "manisan": ["permen", "coklat", "gula", "tebu"],
    "tempat tinggal": ["hotel", "apartemen", "rumah", "emperan"]
}

if __name__ == "__main__":
    permainan = Quartets(dek_kartu)
    permainan.add_player("Asep")
    permainan.add_player("Budi")
    permainan_kwargs = dict()
    result = dict()

    while permainan.state is not Quartets_GameState.FINISHED:
        result = permainan.play(**permainan_kwargs)
        permainan_kwargs = dict()
        print("state", permainan.state)
        print("Current player :", result["current_player"])

        if result["result"]["error"]:
            try:
                print("Error!", result["result"]["errmsg"])
            except KeyError:
                print("Error!")

        if permainan.state is Quartets_GameState.NOT_STARTED:
            print("Game not started yet")

        elif permainan.state is Quartets_GameState.CHOOSE_GROUP:
            print("Group list")
            for k in result["result"]["group"]:
                print(k)
            permainan_kwargs["group"] = input("Select group: ")

        elif permainan.state is Quartets_GameState.CHOOSE_PLAYER:
            print("Owners")
            for k in result["result"]["owner"]:
                print(k)
            permainan_kwargs["target"] = input("Select target player: ")

        elif permainan.state is Quartets_GameState.CHOOSE_CARD:
            print("Cards belong to group " + permainan.current_category)
            for k in result["result"]["cards"]["list"]:
                if k in result["result"]["cards"]["owned"]:
                    print(k + " (owned)")
                else:
                    print(k)
            permainan_kwargs["cardname"] = input("Select card: ")

        elif permainan.state is Quartets_GameState.PLAYER_AGAIN:
            print("Continue!")

        elif permainan.state is Quartets_GameState.PLAYER_NEXT:
            print("Switch player!")
            print("Reason:", result["result"]["msg"])

    print("Game finished!")
    print("Score :")
    for player_id in result["result"]["score"]:
        print(player_id + '\t' + str(result["result"]["score"][player_id]))
