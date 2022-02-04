from agent import Agent
class Knowledge(object):
    """ Knowledge object for all the actual information of the agent\n
        Attributes:
            'my_name': client agent's name
            'my_cards': [list of hintState tuples on agent's cards]
            'my_cards_clued': # of cards clued in agent's hand
            'my_turn': bool
            'my_turn_idx': int

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
            'actual_score': float

            'state': actual state of the enviroment
            'actions': list of possible actions
            'agent': Q-Learning agent
    """
    def __init__(self, playerName, data=None, loaded_learn_qTable=False,training=False) -> None:
        super().__init__()
        if data is not None:
            self.init = True
            self.my_name = playerName
            if len(data.players) < 4:
                self.my_cards = [(None, None, 0) for _ in range(5)]
            else:
                self.my_cards = [(None, None, 0) for _ in range(4)]     
            self.my_cards_clued = 0
            self.handSize = len(self.my_cards)
            self.my_turn = False
            self.my_turn_idx = None

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
            self.actual_score = 0
            # Q-Learning 
            # state: (last_round, state_blueTokens, state_redTokens, state_actualScore, my_cards_clued)
            self.state = (0, 0, 0, 0, 0)
            self.actions = ['play','hint','discard']
            if training:
                epsilon = 0.2
                print("Training mode")
            else:
                epsilon = 0.0 #if it's not training we focus on exploitation and not exploration
                print("Evaluation mode")
            self.agent = Agent(self.state,self.actions, epsilon=epsilon, load_learned=loaded_learn_qTable,save_filename=f"learned_qTable_{self.num_players}.npy")
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

        

        ### Calculating available hints
        if self.blue_tokens > 0:
            # hint actions
            hints_set = set()
            for player in self.players:
                    for card in self.players[player]['cards']:
                        hints_set.add(('hint', player, card.color))
                        hints_set.add(('hint', player, card.value))
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
                + f"Cards remaining: {max(self.num_deck_cards, 0)}\n"
                + "Note tokens used: " + str(8-self.blue_tokens) + "/8" + "\n"
                + "Storm tokens used: " + str(3-self.red_tokens) + "/3" + "\n")

    def state_for_blueTokens(self): # we decrese the state size for blue tokens from 8 to 5
        if self.blue_tokens == 0:
            return 0
        if self.blue_tokens in [1,2]:
            return 1
        if self.blue_tokens in [3,4,5]:
            return 2
        if self.blue_tokens in [6,7]:
            return 3
        return 4 #blue_tokens = 8
    
    def state_for_redTokens(self): # we decrese the state size for blue tokens from 8 to 5
        if self.red_tokens == 0:
            return 3
        if self.red_tokens == 1:
            return 2
        if self.red_tokens == 2:
            return 1
        if self.red_tokens == 3:
            return 0

    def state_for_score(self): # we decrese the state size for scores from 25 to 4
        self.actual_score = sum(self.table_cards.values())
        if self.actual_score < 5:
            return 0
        if self.actual_score >=5 and self.actual_score < 10:
            return 1
        if self.actual_score >=10 and self.actual_score < 20:
            return 2
        return 3 # actual_score >= 20

    def next_state(self):
        return (int(self.last_round),
                self.state_for_blueTokens(),
                self.state_for_redTokens(),
                self.state_for_score(),
                int(self.my_cards_clued > 0))