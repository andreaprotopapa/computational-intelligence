class Knowledge(object):
    """Knowledge object for all the actual information of the agent\n
        'my_name': client agent's name
        'my_cards': [list of hintState tuples on agent's cards]
        'my_cards_clued': # of cards clued in agent's hand
        'my_turn': bool
        'my_turn_idx': int
        'my_available_actions': [list of possible actions for the agent]

        'player_names': [list of all the other players' names]\n
        'players': {'player_name': {'turn': turn, 'cards': [list of Card objs]}}\n
        'num_players': # total number of players\n
        'num_deck_cards': # actual number of desk cards\n
        'table_cards':  {'red':  n_red, 'blue': n_blue, 'yellow': n_yellow, 'green': n_green, 'white': n_white}\n
        'discard_pile': {'red':[n_red], 'blue':[n_blue], 'yellow':[n_yellow], 'green':[n_green], 'white':[n_white]}\n
        'blue_tokens':    # remaining number blue tokens\n 
        'red_tokens': # remaining number red tokens\n

        'player_idx': {'player_name': #turn index}\n
        'idx_player': {'idx_player':  #player name}\n
        'currentPlayer': current player's name\n
        'last_round': bool
    """
    def __init__(self, playerName, data=None) -> None:
        super().__init__()
        if data is not None:
            self.init = True
            self.my_name = playerName
            self.my_cards = [(None, None,0), (None, None,0), (None, None,0), (None, None,0), (None, None,0)]
            self.my_cards_clued = 0
            self.handSize = len(self.my_cards)
            self.my_turn = False
            self.my_turn_idx = None
            self.my_available_actions = []
            self.my_last_remaining_hints = []

            self.player_names = [player.name for player in data.players if player.name != playerName] # all the other players' names

            self.players = dict() # all the other players
            self.num_players = len(data.players) # total number of players
            self.num_deck_cards = int(50 - self.num_players*5)
            self.table_cards = {'red': 0, 'yellow': 0, 'green': 0, 'blue': 0, 'white': 0}
            self.discard_pile = {   'red': {1: 0, 2: 0, 3:0, 4:0, 5:0},
                                    'yellow': {1: 0, 2: 0, 3:0, 4:0, 5:0},
                                    'green': {1: 0, 2: 0, 3:0, 4:0, 5:0},
                                    'blue': {1: 0, 2: 0, 3:0, 4:0, 5:0},
                                    'white': {1: 0, 2: 0, 3:0, 4:0, 5:0}}
            self.blue_tokens = 8
            self.red_tokens = 3

            self.player_idx = {} # ???
            self.idx_player = {} # ???

            for p in self.player_names: #set players
                self.players[p] = {'turn': -1, 'cards': []}
            for i in range(len(data.players)):
                if data.players[i].name == playerName:
                    self.my_turn_idx = i
                else:
                    self.players[data.players[i].name]['turn'] = i
                    self.players[data.players[i].name]['cards'] = data.players[i].hand
                    self.player_idx[data.players[i].name] = i # ???
                    self.idx_player[i] = data.players[i].name # ???
        
            self.current_player = data.currentPlayer
            self.last_round = False
        else:
            self.init = False
            self.my_turn = False
            self.my_name = playerName

    def updateKnowledge(self, data):
        for i in range(len(data.players)): #set cards for each player's hand I can see
            if i != self.my_turn_idx:
                self.players[data.players[i].name]['cards'] = data.players[i].hand

        for color in data.tableCards: #set table cards
            if len(data.tableCards[color]) > 0:
                self.table_cards[color] = max([c.value for c in data.tableCards[color]])

        self.discard_pile = {   'red': {1: 0, 2: 0, 3:0, 4:0, 5:0}, #reset discard pile
                                'yellow': {1: 0, 2: 0, 3:0, 4:0, 5:0},
                                'green': {1: 0, 2: 0, 3:0, 4:0, 5:0},
                                'blue': {1: 0, 2: 0, 3:0, 4:0, 5:0},
                                'white': {1: 0, 2: 0, 3:0, 4:0, 5:0}}
        for card in data.discardPile: #set discard pile
            self.discard_pile[card.color][card.value] += 1

        self.blue_tokens = 8 - data.usedNoteTokens #set remaining clues
        self.red_tokens = 3 - data.usedStormTokens #set remaining mistakes

        ### actions:    ('discard', 3)              --> discard cart 3 
        #               ('play', 5)                 --> play cart 5
        #               ('hint', 'agent_1', 'blue') --> hint player agent_1 'blue'
        #               ('hint', 'agent_2', 1)      --> hint player agent_2 number '1'
        self.my_available_actions = [('play',0), ('play', 1), ('play', 2), ('play', 3), ('play', 4)]  # playing is always permissible (last round?)

        ### Calculating available hints
        if self.blue_tokens > 0:
            # hint actions
            hints_set = set()
            for player in self.players:
                    for card in self.players[player]['cards']:
                        hints_set.add(('hint', player, card.color))
                        hints_set.add(('hint', player, card.value))
            for action in hints_set:
                self.my_available_actions.append(action)
        if self.blue_tokens != 8: # discard is good (so, valid) only if I can get back a blue token
            # discard actions
            if self.last_round:
                self.my_available_actions.extend([('discard',0), ('discard', 1), ('discard', 2), ('discard', 3), ('discard', 4)])
        self.current_player = data.currentPlayer


    def toString(self):
        players_hands = ""
        for p in self.players:
            players_hands += f"\tPlayer {p}:\n"
            for card in self.players[p]['cards']:
                players_hands += f"\t\t({card.color}, {card.value})\n"
        table_cards = ''.join(f"\t{color}: [ {self.table_cards[color]} ]" for color in self.table_cards)
        discard_pile = ''.join([f"\t{color}: [ {self.discard_pile[color]} ]\n" for color in self.discard_pile])
        return (  "\nYour name: " + self.my_name + "\n"
                + "Current player: " + self.current_player + "\n"
                + "Player hands: \n" + players_hands + "\n"
                + f"Cards in your hand: {self.handSize}\n"
                + "Hints for you: " + str(self.my_cards) + "\n"
                + "Table cards: \n" + table_cards + "\n"
                + "Discard pile: \n" + discard_pile + "\n"
                + f"Cards remaining: {self.num_deck_cards}\n"
                + "Note tokens used: " + str(8-self.blue_tokens) + "/8" + "\n"
                + "Storm tokens used: " + str(3-self.red_tokens) + "/3" + "\n")
