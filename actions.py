

def cellar(player):
    discarded = 0
    while player.hand:
        choice = player.choose_card(player.hand, context='cellar')
        if choice == 0:
            break
        d = player.hand.pop(choice - 1)
        player.discard.append(d)
        player.game.notify('discard', player, d)
        discarded += 1
    for i in range(discarded):
        player.draw_card()
        
        
def chapel(player):
    trashed = 0
    while player.hand and trashed <= 4:
        choice = player.choose_card(player.hand, context='chapel')
        if choice == 0:
            break
        d = player.hand.pop(choice - 1)
        player.game.notify('trash', player, d)
        trashed += 1


def council_room(player):
    for p in player.game.players:
        if p != player:
            p.draw_card()


def remodel(player):
    if player.hand:
        choice = player.choose_card(player.hand, context='remodel', skippable=False)
        card = player.hand.pop(choice - 1)
        player.game.notify('trash', player, card)
        buy_options = filter(lambda pile: not pile.empty() and pile.card.cost <= card.cost + 2,
                             player.game.supply.supply.values())
        if buy_options:
            choice = player.choose_buy(buy_options)
            card = player.game.supply.draw(buy_options[choice - 1].card.name)
            player.game.notify('gain', player=player, card=card) 
            player.discard.append(card)
