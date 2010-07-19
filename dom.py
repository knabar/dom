import random
import sys
import actions
import strategies

card_definitions_data = """
NAME            COST    TYPE    TREASUR VICTORY COIN    ACTION  CARD    BUY     PCOST
copper          0       T       1       0       0       0       0       0       0
silver          3       T       2       0       0       0       0       0       0
gold            6       T       3       0       0       0       0       0       0
potion          4       T       0       0       0       0       0       0       0
curse           0       C       0       -1      0       0       0       0       0
estate          2       V       0       1       0       0       0       0       0
duchy           5       V       0       3       0       0       0       0       0
province        8       V       0       6       0       0       0       0       0
market          5       A       0       0       1       1       1       1       0
smithy          3       A       0       0       0       0       3       0       0
festival        5       A       0       0       2       2       0       1       0
laboratory      5       A       0       0       0       1       2       0       0
village         3       A       0       0       0       2       1       0       0
woodcutter      3       A       0       0       2       0       0       1       0
great_hall      3       AV      0       1       0       1       1       0       0
harem           6       TV      2       2       0       0       0       0       0
bazaar          5       A       0       0       1       2       1       0       0
cellar          2       A       0       0       0       1       0       0       0
chapel          2       A       0       0       0       0       0       0       0
council_room    5       A       0       0       0       0       4       1       0
remodel         4       A       0       0       0       0       0       0       0
"""

card_definitions = dict()

for card in filter(lambda l: l and l[0].islower(), card_definitions_data.splitlines()):
    d = dict(zip("name cost type treasure victory coin action card buy potion_cost".split(), card.split()))
    card_definitions[d['name']] = d

playset = [
    'market',
    'remodel',
    'festival',
    'laboratory',
    'village',
    'woodcutter',
    'great_hall',
    'council_room',
    'chapel',
    'cellar',
    ]


class Card(object):
    
    def __init__(self, card):
        for a, v in card_definitions[card].iteritems():
            try:
                v = int(v)
            except ValueError:
                pass
            setattr(self, a, v)
        
    def __str__(self):
        return self.name
        

class Pile(object):
    
    def __init__(self, card, count=10, order=99):
        self.cards = []
        for i in range(count):
            self.cards.append(Card(card))
        self.card = Card(card)
        self.order = order
        self.embargoes = 0
        
    def empty(self):
        return not self.cards
        
    def draw(self):
        return self.cards.pop() if self.cards else None
            
    def __str__(self):
        return '%s $%d [%d]%s' % (self.card.name, self.card.cost, len(self.cards), (' +%d' % self.embargoes) if self.embargoes else '')


class Supply(object):
    
    def __init__(self, players=2):
        supply = [
            Pile('copper', count=40),
            Pile('silver', count=35),
            Pile('gold', count=30),
            Pile('potion', count=20),
            Pile('curse', count=10),
            Pile('estate', count=8 + players * 3),
            Pile('duchy', count=8),
            Pile('province', count=8),
        ]
        for name in playset:
            supply.append(Pile(name))
        self.supply = dict((pile.card.name, pile) for pile in supply)
        
    def game_over(self):
        return len(filter(lambda pile: pile.empty(), self.supply.values())) >= 3 or self.supply['province'].empty()
        
    def draw(self, card):
        return self.supply[card].draw()
        
    def debug(self):
        for pile in sorted(self.supply.values(), key=lambda p: p.order):
            print str(pile)
            
    def cards(self):
        return self.supply.keys()
        
        
class Player(object):
    
    def __init__(self, name):
        self.name = name
        self.draw = []
        self.hand = []
        self.table = []
        self.discard = []
        
    def start_game(self, game):
        self.game = game
        for i in range(3):
            self.discard.append(game.supply.draw('estate'))
        for i in range(7):
            self.discard.append(game.supply.draw('copper'))
        self.cleanup()

    def draw_card(self):
        if not self.draw:
            self.shuffle()
        if self.draw:
            card = self.draw.pop()
            self.hand.append(card)
            self.game.notify('draw', player=self, message='Draws a card', hidden_card=card)
            
    def shuffle(self):
        random.shuffle(self.discard)
        self.draw = self.discard + self.draw
        self.discard = []
    
    def cleanup(self):
        self.game.notify('cleanup', player=self)
        self.discard.extend(self.hand)
        self.discard.extend(self.table)
        self.table = []
        self.hand = []
        for i in range(5):
            self.draw_card()
        self.actions = 1
        self.buys = 1
        self.coins = 0
        
    def play_card(self, card):
        self.game.notify('play', player=self, card=card)
        self.hand.remove(card)
        self.table.append(card)
        for i in range(card.card):
            self.draw_card()
        self.actions += card.action
        self.coins += card.coin
        self.buys += card.buy
        if hasattr(actions, card.name):
            getattr(actions, card.name)(self)
   
    def treasure(self):
        return sum(card.treasure for card in self.table)
    
    def score(self):
        return sum(card.victory for card in (self.hand + self.draw + self.discard + self.table))
    
    def cards_by_type(self, type):
        return filter(lambda card: type in card.type, self.hand)

    def action_phase(self):
        while self.actions:
            action_cards = self.cards_by_type('A')
            if not action_cards: break
            self.game.notify('action_phase', player=self, message='%d action(s) left' % self.actions)
            choice = self.choose_action(action_cards)
            if choice == 0:
                break
            self.play_card(action_cards[choice - 1])
            self.actions -= 1
        
    def buy_phase(self, supply):
        map(self.play_card, self.cards_by_type('T'))
        self.coins += self.treasure()
        while self.buys:
            self.game.notify('buy_phase', player=self, message='%d buy(s) and %s treasure left' % (self.buys, self.coins))
            buy_options = filter(lambda pile: not pile.empty() and pile.card.cost <= self.coins, supply.supply.values())
            choice = self.choose_buy(buy_options)
            if choice == 0:
                break
            card = supply.draw(buy_options[choice - 1].card.name)
            self.game.notify('buy', player=self, card=card) 
            self.discard.append(card)
            self.coins -= card.cost
            self.buys -= 1

    def debug(self, all=False):
        print "Player: %s" % self.name
        print "Hand: %s" % ','.join(map(str, self.hand))
        print "Table: %s" % ','.join(map(str, self.table))
        print "Draw: %s" % (len(self.draw) if not all else ','.join(map(str, self.draw)))
        print "Discard: %s" % (len(self.discard) if not all else ','.join(map(str, self.discard)))


class HumanPlayer(Player):

    def read_number(self, max, skippable=False):
        while True:
            print "Enter choice: ",
            s = sys.stdin.readline()
            try:
                i = int(s)
                if (i <= max) and (i >= (0 if skippable else 1)):
                    return i
            except ValueError:
                pass
            print "Please enter a number between %d and %d" % (0 if skippable else 1, max)

    def choose_card(self, cards, context=None, skippable=True):
        for i, card in enumerate(cards):
            print "%3d: %s" % (i + 1, card)
        return self.read_number(i + 1, True)

    choose_buy = choose_action = choose_card
 
    def notify(self, event, player=None, card=None, message=None):
        print '[%s] %s%s %s %s' % (event, player.name if player else '', ':' if player else '',
                                   message or '', card.name if card else '')
        if event == 'turn' and player == self:
            print "Hand: %s" % ','.join(map(str, self.hand))


class ComputerPlayer(Player):

    def __init__(self, name, strategies):
        super(ComputerPlayer, self).__init__(name)
        self.strategies = strategies
        map(lambda s: s.set_player(self), self.strategies)
        
    def start_game(self, game):
        self.strategies = filter(lambda s: s.applies_to_game(), self.strategies)
        super(ComputerPlayer, self).start_game(game)

    def choose_action(self, action_cards):
        for s in sorted(self.strategies, reverse=True):
            action = s.choose_action(action_cards)
            if action:
                return action
        return 0

    def choose_buy(self, buy_options):
        for s in sorted(self.strategies, reverse=True):
            buy = s.choose_buy(buy_options)
            if buy:
                return buy
        return 0
    
    def choose_card(self, cards, context=None, skippable=True):
        for s in sorted(self.strategies, reverse=True):
            choice = s.choose_card(cards, context, skippable)
            if choice:
                return choice
        return 0 if skippable else 1

    def notify(self, event, player=None, card=None, message=None):
        pass


class Game(object):
    
    def __init__(self, players):
        self.supply = Supply()
        self.players = players
        for player in self.players:
            player.start_game(self)
    
    def notify(self, event, player=None, message=None, card=None, hidden_card=None):
        for p in self.players:
            p.notify(event, player=player, message=message, card=hidden_card if (p == player and hidden_card) else card)
    
    def run(self):
        self.active_player = random.randint(0, len(self.players) - 1)
        self.notify('begin', message='The game begins')
        while not self.supply.game_over():
            player = self.players[self.active_player]
            self.notify('turn', player=player, message='Turn begins')
            player.action_phase()
            player.buy_phase(self.supply)
            player.cleanup()
            self.active_player = (self.active_player + 1) % len(self.players)        
        self.notify('end', message='Game over')
        for player in self.players:
            self.notify('score', player=player, message='Final score %d' % player.score())
            
    def debug(self, all=False):
        print 'Supply:'
        self.supply.debug()
        for player in self.players:
            print
            player.debug(all)
            

if __name__ == '__main__':
    
    print "Welcome to Dominion\n"

    p1 = HumanPlayer('Andreas')
    p2 = ComputerPlayer('Robert', [strategies.BasicStrategy()])
    Game([p1, p2]).run()
    exit()

    wins = [0, 0]
    
    for i in range(100):
        p1 = ComputerPlayer('Andreas', [strategies.BasicStrategy()])
        p2 = ComputerPlayer('Robert', [strategies.BasicStrategy()])
        
        Game([p1, p2]).run()
        
        s1 = p1.score()
        s2 = p2.score()
        if s1 > s2:
            wins[0] += 1
        elif s2 > s1:
            wins[1] += 1
        
    print wins
    
