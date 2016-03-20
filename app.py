
from flask import Flask, render_template, redirect, url_for, request
import json
import pprint
import random
import copy
from collections import deque
from threading import Event

app = Flask(__name__)

class Card(object):

    def __init__(self, c):

        self.name = c["name"]
        self.power = c["power"]
        self.rank = c["rank"]
        self.effect = c["effect"]
        self.entry_effect = c["entryEffect"]

        self.face_up = False
        # At the beginning of every turn, set the health of every face-up card to its power.
        self.health = self.power

    def __repr__(self):
        return "Card[%s, %s%s]" % (self.name, self.power, (", Face-up" if self.face_up else ""))

    def __str__(self):
        return repr(self)


with open("card_list.json") as f:
    cards = json.load(f, object_hook=Card)
    cards = [c for c in cards if isinstance(c.power, int)]

class User(object):

    def __init__(self, id, name, email):
        self.id = id
        self.name = name
        self.email = email

class GamePlayer(User):

    def __init__(self, user, deck):
        super(GamePlayer, self).__init__(user.id, user.name, user.email)

        self.hand = []
        for i in range(2):
            h = deck.pop()
            h.face_up = True
            self.hand.append(h)

        self.stak = deque()
        for i in range(9):
            self.stak.append(deck.pop())

        self.stak[0].face_up = True


    def __repr__(self):
        return pprint.pformat(self.__dict__) #"GamePlayer[%s, %d in hand, %d in stak]" % (self.name, len(self.hand), len(self.stak))

    def __str__(self):
        return repr(self)


class Game(object):

    def __init__(self, users):
        self.deck = copy.deepcopy(cards)
        self.full_deck = list(self.deck) # Keep for usefulness.
        random.shuffle(self.deck)
        self.discarded = []
        self.players = [GamePlayer(u, self.deck) for u in users]
        self.current_player = -1
        self.initial_turn_discard_count = -1
        self.winner = None

        self.next_turn()

    def play_card(self, hand_card_index, target_player_index):
        stak = self.players[target_player_index].stak
        if self.can_play_card(hand_card_index):
            card = self.players[self.current_player].hand.pop(hand_card_index)
            stak.appendleft(card)
            card.face_up = True
        else:
            print "Shouldn't get here - cannot play card from empty hand"

    def _reveal_top_card(self, player_index):
        card = self.players[player_index].stak[0]
        card.face_up = True
        print "Entry effect happens here: %s - %s" % (card.name, card.entry_effect)
        card.health = card.power 

    def discard_stak_card(self, player_index):

        stak = self.players[player_index].stak
        if len(stak) > 1:
            card = stak.popleft()
            self.discarded.append(card)
            self._reveal_top_card(player_index)
        else:
            print "Shouldn't get here - cannot discard to leave empty stak"

    def discard_hand_card(self, hand_card_index):
        if len(self.players[self.current_player].hand) > hand_card_index:
            hand = self.players[self.current_player].hand
            card = hand.pop(hand_card_index)
            self.discarded.append(card)
        else:
            print "Shouldn't get here - cannot discard from empty hand"

    def attack(self, target_player_index):

        if self.can_attack(target_player_index):

            self.attacking_card = self.players[self.current_player].stak[0]
            attacked_card = self.players[target_player_index].stak[0]

            print "Effect happens here: %s - %s" % (self.attacking_card.name, self.attacking_card.effect)
            self.attacking_card.health -= attacked_card.power
            attacked_card.health -= self.attacking_card.power

            if self.attacking_card.health <= 0:
                self.discard_stak_card(self.current_player)

            if attacked_card.health <= 0:
                self.discard_stak_card(target_player_index)

        else:
            print "Should work out what to do here. Shouldn't ever get here."

    def next_turn(self):

        total_cards_discarded = len(self.discarded)

        if self.can_end_turn():
            
            for c in self.full_deck:
                c.health = c.power

            self.current_player = (self.current_player + 1) % len(self.players)

            h = self.deck.pop()
            h.face_up = True
            self.players[self.current_player].hand.append(h)
            
            self.initial_turn_discard_count = len(self.discarded)
            self.attacking_card = None
        else:
            print "Should not have got here - not allowed to end turn yet."

    def can_end_turn(self):
        return self.initial_turn_discard_count < len(self.discarded)

    def can_attack(self, player_index=-1):
        return (self.attacking_card is None or self.attacking_card == self.players[self.current_player].stak[0]) and (player_index == -1 or (len(self.players[player_index].stak) > 0 and player_index != self.current_player))

    def can_discard_hand_card(self, hand_card_index=-1):
        return len(self.players[self.current_player].hand) > hand_card_index

    def can_discard_stack_card(self, player_index=-1):
        return (self.players[player_index].stak) > 1

    def can_play_card(self, hand_card_index=0):
        return len(self.players[self.current_player].hand) > hand_card_index

    def get_current_player(self):
        return self.players[self.current_player]

    def __repr__(self):
        return pprint.pformat(self.__dict__) #"Game[%s]" % ", ".join([str(p) for p in self.players])

    def __str__(self):
        return repr(self)


game = None

def redirect_to_state():
    refresh.set()
    return redirect(url_for("state", player=request.args.get('player', None)))

@app.route("/new_game", methods=["POST"])
def new_game():
    global game
    game = Game([
        User("ipd21", "Ian", "ian@example.com"),
        User("jps79", "James", "James@example.com")
    ])

    return redirect_to_state()
    

@app.route("/end_game", methods=["POST"])
def end_game():
    global game
    game = None
    
    return redirect_to_state()

@app.route("/play_card", methods=["POST"])
def play_card():
    game.play_card(int(request.args.get('index')),game.current_player)

    return redirect_to_state()

@app.route("/discard_hand_card", methods=["POST"])
def discard_hand_card():
    game.discard_hand_card(int(request.args.get('index')))

    return redirect_to_state()

@app.route("/discard_stak_card", methods=["POST"])
def discard_stak_card():
    game.discard_stak_card(game.current_player)

    return redirect_to_state()

@app.route("/attack", methods=["POST"])
def attack():
    game.attack(int(request.args.get('targetPlayerIndex')))

    return redirect_to_state()

@app.route("/next_turn", methods=["POST"])
def next_turn():
    game.next_turn()

    return redirect_to_state()


refresh = Event()
@app.route("/notify")
def notify():
    refresh.wait()
    refresh.clear()
    return ""


@app.route("/")
def state():
    pid = request.args.get('player', None)

    if pid and game and len(game.players) > int(pid):
        player = game.players[int(pid)]
    else:
        player = None

    print player

    return render_template("app.html", game=game, player=player, pid=pid)

@app.route("/card")
def preview_card():
    card_d = {"name": "Hello!", "power": 1, "rank": 1, "effect": "", "entryEffect": ""}
    card = Card(card_d)
    return render_template("card_template.html", c=card)

if __name__ == "__main__":
    app.run(host="0.0.0.0",debug=True, threaded=True)

















