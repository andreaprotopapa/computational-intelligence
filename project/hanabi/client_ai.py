#!/usr/bin/env python3

from sys import argv, stdout
from threading import Thread

from matplotlib.pyplot import table
import GameData
import socket
from constants import *
import os


if len(argv) < 4:
    print("You need the player name to start the game.")
    #exit(-1)
    playerName = "Test" # For debug
    ip = HOST
    port = PORT
else:
    playerName = argv[3]
    ip = argv[1]
    port = int(argv[2])

run = True

statuses = ["Lobby", "Game", "GameHint"]

status = statuses[0]

card_colors = ['red', 'green', 'blue', 'yellow', 'white']

hintState = ("", "")

num_games = 0
average_score = 0.0
num_games_limit = 1

class Info(object):
    """Info object for all the actual information of the agent\n
        'my_name': client agent's name
        'my_cards': [list of hintState tuples on agent's cards]
        'my_cards_clued': # of cards clued in agent's hand
        'my_turn': bool
        'my_available_actions': [list of possible actions for the agent]

        'player_names': [list of all the other players' names]\n
        'players': {'player_name': {'turn': turn, 'cards': [list of Card objs]}}\n
        'num_players': # total number of players\n
        'num_deck_cards': # actual number of desk cards\n
        'table_cards':  {'red':  n_red, 'blue': n_blue, 'yellow': n_yellow, 'green': n_green, 'white': n_white}\n
        'discard_pile': {'red':[n_red], 'blue':[n_blue], 'yellow':[n_yellow], 'green':[n_green], 'white':[n_white]}\n
        'rem_clues':    # remaining number blue tokens\n 
        'rem_mistakes': # remaining number red tokens\n

        'player_idx': {'player_name': #turn index}\n
        'idx_player': {'idx_player':  #player name}\n
        'currentPlayer': current player's name\n
        'last_round': bool
    """
    def __init__(self, data=None) -> None:
        super().__init__()
        if data is not None:
            self.init = True
            self.my_name = playerName
            self.my_cards = [(None, None), (None, None), (None, None), (None, None), (None, None)]
            self.my_cards_clued = 0
            self.handSize = len(self.my_cards)
            self.my_turn = False
            self.my_available_actions = []

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
            self.rem_clues = 8
            self.rem_mistakes = 3

            self.player_idx = {} # ???
            self.idx_player = {} # ???

            for p in self.player_names: #set players
                self.players[p] = {'turn': -1, 'cards': []}
            for i in range(len(data.players)):
                if data.players[i].name == playerName:
                    self.my_turn = i
                else:
                    self.players[data.players[i].name]['turn'] = i
                    self.players[data.players[i].name]['cards'] = data.players[i].hand
                    self.player_idx[data.players[i].name] = i # ???
                    self.idx_player[i] = data.players[i].name # ???
        
            self.currentPlayer = data.currentPlayer
            self.last_round = False
        else:
            self.init = False

    def updateInfo(self, data):
        for i in range(len(data.players)): #set cards for each player's hand I can see
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

        self.rem_clues = 8 - data.usedNoteTokens #set remaining clues
        self.rem_mistakes = 3 - data.usedStormTokens #set remaining mistakes

        ### actions:    ('discard', 3)              --> discard cart 3 
        #               ('play', 5)                 --> play cart 5
        #               ('hint', 'agent_1', 'blue') --> hint player agent_1 'blue'
        #               ('hint', 'agent_2', 1)      --> hint player agent_2 number '1'
        self.my_available_actions = [('play',0), ('play', 1), ('play', 2), ('play', 3), ('play', 4)]  # playing is always permissible (last round?)

        ### Calculating available hints
        if self.rem_clues > 0:
            # hint actions
            hints_set = set()
            for player in self.players:
                    for card in self.players[player]['cards']:
                        hints_set.add(('hint', player, card.color))
                        hints_set.add(('hint', player, card.value))
            for action in hints_set:
                self.my_available_actions.append(action)
        if self.rem_clues != 8: # discard is good (so, valid) only if I can get back a blue token
            # discard actions
            if self.last_round:
                self.available_actions.extend([('discard',0), ('discard', 1), ('discard', 2), ('discard', 3), ('discard', 4)])
        self.currentPlayer = data.currentPlayer

    def toString(self):
        players_hands = ''.join("Player " + p + " " + map(str, self.players[p]['cards'])+'\n' for p in self.player_names)
        table_cards = ''.join("\t" + color + ": [" + self.table_cards[color] +"]" for color in self.table_cards)
        discard_pile = ''.join("\t" + color + ": [ " + self.discard_pile[color] +" ]" for color in self.discard_pile)
        return (  "Your name: " + self.my_name + "\n"
                + "Current player: " + self.currentPlayer + "\n"
                + "Player hands: \n" + players_hands + "\n"
                + "Cards in your hand: " + self.handSize + "\n"
                + "Hints for you: " + str(self.my_cards) + "\n"
                + "Table cards: \n" + table_cards + "\n"
                + "Discard pile: \n" + discard_pile + "\n"
                + "Note tokens used: " + str(self.rem_clues) + "/8" + "\n"
                + "Storm tokens used: " + str(self.rem_mistakes) + "/3" + "\n")

my_info = Info() # all agent knowledge is here


def parse_game_data(my_info: Info, data):
        if my_info.init is False: #init Info
            my_info = Info(data)
        else:
            my_info.updateInfo(data)
        print(my_info.toString())

def discard_feedback(my_info: Info, data):
    my_info.num_deck_cards -= 1
    my_info.info['rem_clues'] += 1
    if data.handLength < 5:
        my_info.last_round = True
    if data.lastPlayer == my_info.my_name:
        if True: # self.verbose_action:
            print("Card discarded!")
        if my_info.my_cards[data.cardHandIndex][0] != None or my_info.my_cards[data.cardHandIndex][1] != None:
            my_info.my_cards_clued -= 1
        my_info.my_cards[data.cardHandIndex] = (None, None)

def niceMove_feedback(my_info: Info, data):
    my_info.num_deck_cards -= 1
    #TODO (Apparantly not supported by the server!)
    # if data.card.value == 5 and my_info.rem_clues < 8:
    #     my_info.rem_clues += 1
    if data.handLength < 5:
        my_info.last_round = True
    if data.lastPlayer == my_info.my_name:
        if True: # self.verbose_action:
            print("Card played successfully!")
        if my_info.my_cards[data.cardHandIndex][0] != None or my_info.my_cards[data.cardHandIndex][1] != None:
            my_info.my_cards_clued -= 1
        my_info.my_cards[data.cardHandIndex] = (None, None)

def badMove_feedback(my_info: Info, data):
    my_info.num_deck_cards -= 1
    my_info.rem_mistakes -= 1
    if data.handLength < 5:
        my_info.last_round = True
    if data.lastPlayer == my_info.my_name:
        if True: #self.verbose_action:
            print("Card misplayed!")
        if my_info.my_cards[data.cardHandIndex][0] != None or my_info.my_cards[data.cardHandIndex][1] != None:
            my_info.my_cards_clued -= 1
        my_info.my_cards[data.cardHandIndex] = (None, None)

def parse_hint_data(my_info: Info, data):
    hint = {'giver'     :   data.source,
            'receiver'  :   data.destination, 
            'type'      :   data.type,
            'val'       :   data.value,
            'positions' :   data.positions}
    my_info.rem_clues -= 1
    if hint['receiver'] == my_info.my_name:
        for i in hint['positions']:
            ### THEORY OF MIND: To avoid misplays, we only memorize the first position !!!
            if hint['type'] == 'value':
                if my_info.my_cards[i][0] == None and my_info.my_cards[i][1] == None:
                    my_info.my_cards_clued += 1
                my_info.my_cards[i] = (hint['val'], my_info.my_cards[i][1])
            else:
                if my_info.my_cards[i][0] == None and my_info.my_cards[i][1] == None:
                    my_info.my_cards_clued += 1
                my_info.my_cards[i] = (my_info.my_cards[i][0], hint['val'])
            break
    
    #my_info.hint_history.add((data.source, data.destination, data.type, data.value))

    """ reward = self.info['rem_clues']-self.num_players

    next_state = (int(self.last_round), self.coarse_coding_rem_clues(),\
            3-self.info['rem_mistakes'], self.coarse_coding_score(), int(self.my_cards_clued > 0))
    if next_state not in self.q_table:
        self.q_table[next_state] = [0.,0.,0.]
    self.q_table[self.state][1] = self.q_table[self.state][1] + self.alpha*(reward\
        + self.gamma*self.q_table[next_state][np.argmax(self.q_table[next_state])] -\
                self.q_table[self.state][1])
    self.state = next_state """

def process_game_over(my_info: Info, score):
    global run
    global num_games
    global average_score
    global num_games_limit
    print(f"\nThis game is over with final score {score}. "
    f"{max(my_info.num_deck_cards, 0)} cards remained in the deck. The final table cards: {my_info.table_cards}. ")
    my_info = Info() #reset info

    num_games += 1
    average_score = (average_score * (num_games-1)+score)/num_games
    print(f"Games played so far: {num_games}. Average score in the tournament so far: {average_score}")
    print("Beginning a new game...")
    ## For DEBUGGING
    #tmp = input()
    if num_games_limit != None:
        if num_games >= num_games_limit:
            run = False

def is_hint_safe(hint):
    cards = my_info.players[hint[1]]['cards'] #cards of the player "hinted"
    if hint[2] == 'value':
        for i in range(hint[4]): # for all cards before the hinted one
            if cards[i].value == hint[3]: # if the card hinted as the same value of a card before it
                return False
    else:
        for i in range(hint[4]):
            if cards[i].color == hint[3]:
                return False
    return True
             
def compare_hints(value_hint, color_hint): #count how many cards are touched giving value hint or color hint
        cards = my_info.players[value_hint[1]]['cards'] 
        touched_v = 0
        touched_c = 0
        for card in cards:
            if card.value == value_hint[3]:
                touched_v += 1
            if card.color == color_hint[3]:
                touched_c += 1
        if touched_v<=touched_c:
            return 0
        return 1

def select_action():
        ### hard-coded agent
        ## Iterate over your cards and play the most recent hinted card
        for i, card in enumerate(my_info.my_cards):
            value_hint = card[0]
            color_hint = card[1]
            ## prioritize completely known cards (both color and value) over others (and play, discard, or keep it)
            if  value_hint != None and color_hint != None: #if I have two hints on that card
                ## play
                if my_info.table_cards[color_hint]+1 == value_hint:
                    return ('play', i)
                ## discard the useless card if possible
                elif my_info.table_cards[color_hint]+1 > value_hint and my_info.rem_clues < 8:
                    return ('discard', i)
            ## Prioritize value hints over color hints 
            if value_hint != None:
                ## Check if there exists a deck that actually fits this hint and then play; otherwise try to discard it.
                for color in card_colors:
                    if my_info.table_cards[color]+1 == value_hint:
                        return ('play', i)
                if my_info.rem_clues < 8:
                    return ('discard', i)
            if color_hint != None:
                ## Check if there exists a deck that actually fits this hint and then play; otherwise try to discard it.
                for color in card_colors:
                    if my_info.table_cards[color] != 5:
                        return ('play', i)
                if my_info.rem_clues < 8:
                    return ('discard', i)

        ## Iterate over your teammates' hands and hint any immediate play (hint first to the opponents that play sooner.)
        ## Care ADDED about other cards that may be touched!
        if my_info.rem_clues > 0:
            next_player_idx = (my_info.my_turn + 1) % my_info.num_players
            for i in range(my_info.num_players-1):
                player_name = my_info.idx_player[next_player_idx]
                player_cards = my_info.players[player_name]['cards']
                for i, card in enumerate(player_cards):
                    if my_info.table_cards[card.color]+1 == card.value: # player has the next card for that color
                        hint_value = (my_info.my_name, player_name, 'value', card.value, i)
                        hint_color = (my_info.my_name, player_name, 'color', card.color, i)
                        ## Give a hint that touches fewer cards
                        if compare_hints(hint_value, hint_color) == 0: # hint on value touches less cards
                            ### THEORY OF MIND: To avoid misplays, we only give hints that do not touch dangerous cards before the hinted one
                            if is_hint_safe(hint_value):
                                return ('hint', player_name, hint_value[3])
                        else: # hint on color touches less cards
                            ### THEORY OF MIND: To avoid misplays, we only give hints that do not touch dangerous cards before the hinted one
                            if is_hint_safe(hint_color):
                                return ('hint', player_name, hint_color[3])

                next_player_idx = (next_player_idx + 1) % my_info.num_players

        ## Last round (play the newest card if we have more than one storm tokens available)
        if my_info.last_round:
            if my_info.rem_mistakes > 1:
                return ('play', 0)

        ## Discard your last unclued card
        if my_info.rem_clues < 8:
            for i in range(len(my_info.my_cards)-1, -1, -1): #from my last card
                if my_info.my_cards[i][0] == None and my_info.my_cards[i][1] == None: #if it's totally unclued
                    if i == 4 and my_info.last_round:
                        return ('discard', i-1)
                    else:
                        return ('discard', i-1)

        """ ## Using the q-table (that is being updated constantly) to choose an action as a last resort 
        a = np.argmax(self.q_table[self.state])
        if a == 1 and self.info['rem_clues'] == 0:
            a = 0
        if a == 0 and self.info['rem_clues'] == 8:
            a = 1

        if a == 0:
            ## dicard
            for idx, card in enumerate(self.my_cards):
                if card[0] == None and card[1] == None:
                    return ('d', idx)
            for idx, card in enumerate(self.my_cards):
                if card[0] == None or card[1] == None:
                    return ('d', idx)
            if self.last_round:
                return ('d', 3)
            else:
                return ('d', 4)

        if a == 1:
            ## hint; Hint color to the last card of the furthest player to delay any possible misplay.
            if self.turn == 0:
                furthest_player_idx = self.num_players-1
            else:
                furthest_player_idx = self.turn-1
            p_name = self.idx_player[furthest_player_idx]
            if self.last_round:
                card = self.info['players'][self.idx_player[furthest_player_idx]]['cards'][3]
            else:
                card = self.info['players'][self.idx_player[furthest_player_idx]]['cards'][4]
            hint_color = (self.name, p_name, 'value', card.color)
            return ('h', p_name, hint_color[3])
        
        if a == 2:
            ## Play your newest card
            return ('p', 0) """

def action_to_command(action):
        if action[0] == 'discard':  
            # discard
            command = f"discard {action[1]}"
        elif action[0] == 'play':
            # play
            command = f"play {action[1]}"    
        else:
            if type(action[2]) == str:
                # hint color
                command = f"hint color {action[1]} {action[2]}"
            else:
                # hint value
                command = f"hint value {action[1]} {action[2]}"
        return command

def manageInput():
    command = input() ## Give the ready command
    global run
    global status
    while run:
        if status != "Lobby": 
            s.send(GameData.ClientGetGameStateRequest(playerName).serialize()) #like "show" command in client.py, it gives the actual knowledge for the actual player
            my_info.my_turn = False
            action = select_action()
            command = action_to_command(action)
            if True: # if verbose_action:
                print(command)

        # Choose data to send
        if command == "exit":
            run = False
            os._exit(0)

        elif command == "ready" and status == "Lobby":
            s.send(GameData.ClientPlayerStartRequest(playerName).serialize())
            while status == 'Lobby':
                ### Wait in the lobby until the game starts
                continue
        #elif command == "show" and status == "Game":
         #   s.send(GameData.ClientGetGameStateRequest(playerName).serialize())

        elif command.split(" ")[0] == "discard" and status == "Game":
            try:
                cardStr = command.split(" ")
                cardOrder = int(cardStr[1])
                s.send(GameData.ClientPlayerDiscardCardRequest(playerName, cardOrder).serialize())
            except:
                print("Maybe you wanted to type 'discard <num>'?")
                continue

        elif command.split(" ")[0] == "play" and status == "Game":
            try:
                cardStr = command.split(" ")
                cardOrder = int(cardStr[1])
                s.send(GameData.ClientPlayerPlayCardRequest(playerName, cardOrder).serialize())
            except:
                print("Maybe you wanted to type 'play <num>'?")
                continue

        elif command.split(" ")[0] == "hint" and status == "Game":
            try:
                destination = command.split(" ")[2]
                t = command.split(" ")[1].lower()
                if t != "colour" and t != "color" and t != "value":
                    print("Error: type can be 'color' or 'value'")
                    continue
                value = command.split(" ")[3].lower()
                if t == "value":
                    value = int(value)
                    if int(value) > 5 or int(value) < 1:
                        print("Error: card values can range from 1 to 5")
                        continue
                else:
                    if value not in ["green", "red", "blue", "yellow", "white"]:
                        print("Error: card color can only be green, red, blue, yellow or white")
                        continue
                s.send(GameData.ClientHintData(playerName, destination, t, value).serialize())
            except:
                print("Maybe you wanted to type 'hint <type> <destinatary> <value>'?")
                continue

        elif command == "":
            continue

        else:
            print("Unknown command: " + command)
            continue
        stdout.flush()

with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
    request = GameData.ClientPlayerAddData(playerName)
    s.connect((HOST, PORT))
    s.send(request.serialize())
    data = s.recv(DATASIZE)
    data = GameData.GameData.deserialize(data)
    if type(data) is GameData.ServerPlayerConnectionOk:
        print("Connection accepted by the server. Welcome " + playerName)
    print("[" + playerName + " - " + status + "]: ", end="")
    Thread(target=manageInput).start()
    while run:
        dataOk = False
        data = s.recv(DATASIZE)
        if not data:
            continue
        data = GameData.GameData.deserialize(data)

        if type(data) is GameData.ServerPlayerStartRequestAccepted:
            dataOk = True
            print("Ready: " + str(data.acceptedStartRequests) + "/"  + str(data.connectedPlayers) + " players")
            data = s.recv(DATASIZE)
            data = GameData.GameData.deserialize(data)

        if type(data) is GameData.ServerStartGameData:
            dataOk = True
            print("Game start!")
            s.send(GameData.ClientPlayerReadyData(playerName).serialize())
            status = "Game"

        if type(data) is GameData.ServerGameStateData: ### done
            dataOk = True
            parse_game_data(my_info, data)

        if type(data) is GameData.ServerActionInvalid:
            dataOk = True
            print("Invalid action performed. Reason:")
            print(data.message)

        if type(data) is GameData.ServerActionValid: #discard feedback
            dataOk = True
            print("Discard action valid!")
            print("Current player: " + data.player)
            discard_feedback(my_info, data)

        if type(data) is GameData.ServerPlayerMoveOk: #good play feedback
            dataOk = True
            print("Nice move!")
            print("Current player: " + data.player)
            niceMove_feedback(my_info,data)

        if type(data) is GameData.ServerPlayerThunderStrike: #bad play feedback
            dataOk = True
            print("OH NO! The Gods are unhappy with you!")
            badMove_feedback(my_info, data)

        if type(data) is GameData.ServerHintData: #hint given to this agent
            dataOk = True
            parse_hint_data(my_info, data)
            print("Hint type: " + data.type)
            print("Player " + data.destination + " cards with value " + str(data.value) + " are:")
            for i in data.positions:
                print("\t" + str(i))

        if type(data) is GameData.ServerInvalidDataReceived:
            dataOk = True
            print(data.data)

        if type(data) is GameData.ServerGameOver:
            dataOk = True
            print(data.message)
            print(data.score)
            print(data.scoreMessage)
            stdout.flush()
            #run = False
            print("Ready for a new game!")
            process_game_over(my_info, data.score)

        if not dataOk:
            print("Unknown or unimplemented data type: " +  str(type(data)))

        print("[" + playerName + " - " + status + "]: ", end="")
        stdout.flush()