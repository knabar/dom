

class Strategy(object):
    
    def __init__(self, weight=1.0):
        self.weight = weight

    def set_player(self, player):
        self.player = player
    
    def __lt__(self, other):
        return self.weight < other.weight
    
    def adjust_weight(self):
        pass
    
    def applies_to_game(self):
        return False
    
    def choose_action(self, action_cards):
        return 0
        
    def choose_buy(self, buy_options):
        return 0
    
    def choose_card(self, cards, context=None, skippable=True):
        return 0
        
        
class BasicStrategy(Strategy):
    
    def applies_to_game(self):
        return True

    def choose_buy(self, buy_options):
        pref = ['province', 'gold', 'duchy', 'silver', 'estate', 'copper']
        for p in pref:
            for i, pile in enumerate(buy_options):
                if pile.card.name == p:
                    return i + 1
        return 0


class DrawCardsStrategy(Strategy):
    
    def applies_to_game(self):
        self.cards = ['market', 'village', 'laboratory', 'great_hall', 'bazaar']
        hits = 0
        for c in self.player.game.supply.cards():
            if c in self.cards:
                hits += 1
        return hits > 0
    
    def choose_action(self, action_cards):
        for c in action_cards:
            if c.name in self.cards