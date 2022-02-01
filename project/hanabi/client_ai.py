#!/usr/bin/env python3

from sys import argv, stdout
from threading import Thread

from matplotlib.pyplot import table
import GameData
import socket
from constants import *
import os
import time
from knowledge import Knowledge


if len(argv) < 5:
    print("You need the player name to start the game.")
    print("You need to specify if you want out results in a file (True/False).")
    #exit(-1)
    playerName = "Test" # For debug
    ip = HOST
    port = PORT
    results = True
    num_games_limit = 2
else:
    playerName = argv[3]
    ip = argv[1]
    port = int(argv[2])
    results = argv[4] == "True"
    num_games_limit = int(argv[5])

run = True

debug = False

statuses = ["Lobby", "Game", "GameHint"]

status = statuses[0]

card_colors = ['red', 'green', 'blue', 'yellow', 'white']

hintState = ("", "")

num_games = 0
average_score = 0.0

update = True
sleeptime = 0.01
before_action = True

my_knowledge = Knowledge(playerName) # all agent knowledge is here

def set_knowledge(data):
    global my_knowledge
    if my_knowledge.init is False: #init Info
        my_knowledge = Knowledge(playerName,data)
    else:
        my_knowledge.updateKnowledge(data)
    time.sleep(sleeptime)
    if data.currentPlayer == playerName and update:
            my_knowledge.my_turn = True
            print(my_knowledge.toString())

def discard_update(data):
    global my_knowledge 
    my_knowledge.num_deck_cards -= 1
    my_knowledge.blue_tokens += 1
    if data.handLength < 5:
        my_knowledge.last_round = True
    if data.lastPlayer == my_knowledge.my_name:
        if my_knowledge.my_cards[data.cardHandIndex][0] != None or my_knowledge.my_cards[data.cardHandIndex][1] != None: #if I had clues on that card
            my_knowledge.my_cards_clued -= 1
        my_knowledge.my_cards.pop(data.cardHandIndex)
        my_knowledge.my_cards.append((None, None, 0))

def niceMove_update(data):
    global my_knowledge
    my_knowledge.num_deck_cards -= 1
    #TODO (Apparantly not supported by the server!)
    # if data.card.value == 5 and my_knowledge.blue_tokens < 8:
    #     my_knowledge.blue_tokens += 1
    if data.handLength < 5:
        my_knowledge.last_round = True
    if data.lastPlayer == my_knowledge.my_name:
        if my_knowledge.my_cards[data.cardHandIndex][0] != None or my_knowledge.my_cards[data.cardHandIndex][1] != None: #if I had clues on that card
            my_knowledge.my_cards_clued -= 1
        my_knowledge.my_cards.pop(data.cardHandIndex)
        my_knowledge.my_cards.append((None, None, 0))

def badMove_update(data):
    global my_knowledge
    my_knowledge.num_deck_cards -= 1
    my_knowledge.red_tokens -= 1
    if data.handLength < 5:
        my_knowledge.last_round = True
    if data.lastPlayer == my_knowledge.my_name: #my fault
        if my_knowledge.my_cards[data.cardHandIndex][0] != None or my_knowledge.my_cards[data.cardHandIndex][1] != None: #if I had clues on that card
            my_knowledge.my_cards_clued -= 1
        my_knowledge.my_cards.pop(data.cardHandIndex)
        my_knowledge.my_cards.append((None, None, 0))


def set_new_hint(hint):
    global my_knowledge

    my_knowledge.blue_tokens -= 1
    if hint.destination == my_knowledge.my_name:
        for i in hint.positions:
            if hint.type == 'value':
                if my_knowledge.my_cards[i][0] == None and my_knowledge.my_cards[i][1] == None:
                    my_knowledge.my_cards_clued += 1
                my_knowledge.my_cards[i] = (hint.value, my_knowledge.my_cards[i][1],1)
            else:
                if my_knowledge.my_cards[i][0] == None and my_knowledge.my_cards[i][1] == None:
                    my_knowledge.my_cards_clued += 1
                my_knowledge.my_cards[i] = (my_knowledge.my_cards[i][0], hint.value,1)
    
    #my_knowledge.hint_history.add((data.source, data.destination, hint.type, hint.value))

    """
    # Q-Learning part
    reward = self.info['blue_tokens']-self.num_players

    next_state = (int(self.last_round), self.coarse_coding_blue_tokens(),\
            3-self.info['red_tokens'], self.coarse_coding_score(), int(self.my_cards_clued > 0))
    if next_state not in self.q_table:
        self.q_table[next_state] = [0.,0.,0.]
    self.q_table[self.state][1] = self.q_table[self.state][1] + self.alpha*(reward\
        + self.gamma*self.q_table[next_state][np.argmax(self.q_table[next_state])] -\
                self.q_table[self.state][1])
    self.state = next_state """

def game_over(score):
    global my_knowledge
    global run
    global num_games
    global average_score
    global num_games_limit
    global update
    global before_action
    global results
    print(f"\nGame n.{num_games}: score {score}.")
    print(f"{max(my_knowledge.num_deck_cards, 0)} still in the deck.")
    print(f"Final table cards: {my_knowledge.table_cards}.")
    
    if results:
        if num_games == 0: 
            mode = "w"
        else:
            mode = "a"
        with open(f"results_{my_knowledge.num_players}.txt", mode) as file_out:
            file_out.write(f"Game n.{num_games}: {score} \n")

    num_games += 1
    average_score = (average_score * (num_games-1)+score)/num_games
    print(f"Games played so far: {num_games}. Actual average score: {average_score}")

    if num_games_limit != None:
        if num_games >= num_games_limit:
            run = False
            print("Log out")
            if results:
                with open(f"results_{my_knowledge.num_players}.txt", "a") as file_out:
                    file_out.write(f"----------------------------\n")
                    file_out.write(f"Avarage score: {average_score}\n")
            os._exit(0)
        else:
            print("Beginning a new game...")
            update = True
            before_action = True
            my_knowledge = Knowledge(playerName) #reset info

def is_hint_safe(hint):
    cards = my_knowledge.players[hint[1]]['cards'] #cards of the player "hinted"
    if hint[2] == 'value':
        for i in range(hint[4]+1,len(cards)): # for all cards before the hinted one
            if cards[i].value == hint[3]: # if the card hinted has the same value of a card before it
                return False
    else:
        for i in range(hint[4]+1,len(cards)):
            if cards[i].color == hint[3]:
                return False
    return True

def is_hint_not_misunderstandable(hint,real_color): #if there is already a card on the table that is the card before the hinted one is misunderstandable!!!
    if hint[2] == 'value' and hint[3]!=1:
        for color in card_colors:
            if color != real_color:
                if my_knowledge.table_cards[color]+1 == hint[3]:
                    return False
    return True
    
def compare_hints(value_hint, color_hint): #count how many cards are touched giving value hint or color hint
        cards = my_knowledge.players[value_hint[1]]['cards'] 
        touched_from_valueHint = 0
        touched_from_colorHint = 0
        for card in cards:
            if card.value == value_hint[3]:
                touched_from_valueHint += 1
            if card.color == color_hint[3]:
                touched_from_colorHint += 1
        if touched_from_valueHint<=touched_from_colorHint:
            return 0 #return 0 if we touch less cards with value hint
        return 1 #return 1 if we touch less cards with value hint

def useful_for_later(value_hint):
    for color in card_colors:
        if my_knowledge.table_cards[color] < value_hint:
            return True
    return False        

def last_remaining(card):
            if card.value == 5:
                return True
            if card.value == 4 and my_knowledge.discard_pile[card.color][card.value] == 1:
                return True
            if card.value == 3 and my_knowledge.discard_pile[card.color][card.value] == 1:
                return True
            if card.value == 2 and my_knowledge.discard_pile[card.color][card.value] == 1:
                return True
            if card.value == 1 and my_knowledge.discard_pile[card.color][card.value] == 2:
                return True
            return False

def select_action():
        # HARD-CODED AGENT
        # Hint dangerous cases
        # next_player_idx = (my_knowledge.my_turn_idx + 1) % my_knowledge.num_players
        # for _ in range(my_knowledge.num_players-1): #for all the other players
        #     player_name = my_knowledge.idx_player[next_player_idx]
        #     player_cards = my_knowledge.players[player_name]['cards']
        #     for i, card in enumerate(player_cards): #for all player's cards
        #         if last_remaining(card):
        #             hint_value = (my_knowledge.my_name, player_name, 'value', card.value, i)
        #             return ('hint', player_name, hint_value[3])
        #     next_player_idx = (next_player_idx + 1) % my_knowledge.num_players

        ## Last round (play the newest card if we have more than one storm tokens available)
        if my_knowledge.last_round:
            if my_knowledge.red_tokens > 1 and my_knowledge.num_deck_cards > 0:
                return ('play', my_knowledge.handSize -1 )
            # elif my_knowledge.blue_tokens < 8 and my_knowledge.num_deck_cards > 0:
            #     return ('discard', 0)
            # else:
            #     player_name =  my_knowledge.player_names[0]
            #     return ('hint', player_name, my_knowledge.players[player_name]['cards'][0].value) #random hint as last chance for very last

        # Play/Discard rules with hints 
        for i, card in reversed(list(enumerate(my_knowledge.my_cards))): # look from the newest card (= the most right)
            value_hint = card[0]
            color_hint = card[1]
            age_hint = card[2]
            # prioritize "completely known" cards (both color and value)
            if  value_hint != None and color_hint != None: #if I have two hints on that card
                # play
                if my_knowledge.table_cards[color_hint]+1 == value_hint:
                    return ('play', i)
            # Prioritize value hints over color hints 
            if value_hint != None and color_hint == None: # CONVENTION: Value Hint --> Keep for later
                ## Check if there exists a firework that actually fits this hint and then play; otherwise try to discard it.
                for color in card_colors:
                    if my_knowledge.table_cards[color]+1 == value_hint and age_hint == 1:
                        return ('play', i)
            if color_hint != None and value_hint == None: # CONVENTION: Color Hint --> Play it immediately
                ## Check if there exists a firework that actually misses cards and if the hint is new
                if my_knowledge.table_cards[color_hint] != 5: 
                    if age_hint == 1:
                        return ('play', i)

        # Hint rules
        if my_knowledge.blue_tokens > 0:
            next_player_idx = (my_knowledge.my_turn_idx + 1) % my_knowledge.num_players
            for _ in range(my_knowledge.num_players-1): #for all the other players
                player_name = my_knowledge.idx_player[next_player_idx]
                player_cards = my_knowledge.players[player_name]['cards']
                for i, card in reversed(list(enumerate(player_cards))): #for all player's cards
                    if my_knowledge.table_cards[card.color]+1 == card.value: # player has the next card for that color
                        hint_value = (my_knowledge.my_name, player_name, 'value', card.value, i)
                        hint_color = (my_knowledge.my_name, player_name, 'color', card.color, i)
                        # Give a hint that touches fewer cards
                        if compare_hints(hint_value, hint_color) == 0 or hint_value == 1: # hint on value touches less cards
                            if is_hint_safe(hint_value): # To avoid misplays, we only give hints that do not touch dangerous cards before the hinted one
                            #if is_hint_not_misunderstandable(hint_value,card.color):
                                return ('hint', player_name, hint_value[3])
                            elif is_hint_safe(hint_color):
                                return ('hint', player_name, hint_color[3])
                        else: # hint on color touches less cards
                            if is_hint_safe(hint_color): # To avoid misplays, we only give hints that do not touch dangerous cards before the hinted one
                                return ('hint', player_name, hint_color[3])
                for i, card in enumerate(player_cards): #for all player's cards
                    if last_remaining(card):
                        if card not in my_knowledge.my_last_remaining_hints:
                            my_knowledge.my_last_remaining_hints.append(card)
                            hint_value = (my_knowledge.my_name, player_name, 'value', card.value, i)
                            if is_hint_not_misunderstandable(hint_value,card.color):
                                return ('hint', player_name, hint_value[3])
                next_player_idx = (next_player_idx + 1) % my_knowledge.num_players

        ## Discard your oldest unclued card (oldest --> most left)
        if my_knowledge.blue_tokens < 8:
             for i, card in enumerate(my_knowledge.my_cards): #from my oldest card ( = the first in the list)
                value_hint = card[0]
                color_hint = card[1]
                age_hint = card[2]
                if value_hint == None and color_hint == None: #if it's totally unclued
                    return ('discard', i)
                if value_hint != None and color_hint == None:
                    if not useful_for_later(value_hint):
                        return ('discard', i)
                if color_hint != None and value_hint == None: 
                    if my_knowledge.table_cards[color_hint] == 5: 
                        return ('discard', i)
                if  value_hint != None and color_hint != None: #if I have two hints on that card
                    if my_knowledge.table_cards[color_hint]+1 > value_hint:
                        return ('discard', i)
        print("AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA")
        if my_knowledge.blue_tokens < 8:
            return ('discard', 0)
        else:
            next_player_idx = (my_knowledge.my_turn_idx + 1) % my_knowledge.num_players #try to suggest to KEEP A CARD for later
            for _ in range(my_knowledge.num_players-1): #for all the other players
                player_name = my_knowledge.idx_player[next_player_idx]
                player_cards = my_knowledge.players[player_name]['cards']
                for i, card in enumerate(player_cards): #for all player's cards
                    if my_knowledge.table_cards[card.color] < card.value: # player has a next card for that color
                        hint_value = (my_knowledge.my_name, player_name, 'value', card.value, i)
                        if is_hint_not_misunderstandable(hint_value,card.color):
                            print("KEEP IT")
                            return ('hint', player_name, hint_value[3])
                next_player_idx = (next_player_idx + 1) % my_knowledge.num_players
            next_player_idx = (my_knowledge.my_turn_idx + 1) % my_knowledge.num_players #all cards of all players are useless also for the future, suggest to DISCARD
            for _ in range(my_knowledge.num_players-1): #for all the other players
                player_name = my_knowledge.idx_player[next_player_idx]
                player_cards = my_knowledge.players[player_name]['cards']
                for i, card in enumerate(player_cards): #for all player's cards
                    hint_value = (my_knowledge.my_name, player_name, 'value', card.value, i)
                    hint_color = (my_knowledge.my_name, player_name, 'color', card.color, i)
                    print("DISCARD IT")
                    ## Give a hint that touches more cards
                    if compare_hints(hint_value, hint_color) == 0: # hint on value touches more cards (to be discarded)
                            return ('hint', player_name, hint_color[3])
                    else: # hint on color touches more cards (to be discarded)
                            return ('hint', player_name, hint_value[3])
                next_player_idx = (next_player_idx + 1) % my_knowledge.num_players
        

        #THIS PART WOULD BE CHANGE WITH QL LEARNING
        # else: #I cannot discard neither play hinted cards: i hint card less useful --> "i suggest you to discard it or keep it for later"
        #     if my_knowledge.blue_tokens > 0:
        #         print("\nLAST CASE!\n")
        #         next_player_idx = (my_knowledge.my_turn_idx + 1) % my_knowledge.num_players #try to suggest to KEEP A CARD for later
        #         for _ in range(my_knowledge.num_players-1): #for all the other players
        #             player_name = my_knowledge.idx_player[next_player_idx]
        #             player_cards = my_knowledge.players[player_name]['cards']
        #             for i, card in enumerate(player_cards): #for all player's cards
        #                 if last_remaining(card):
        #                     hint_value = (my_knowledge.my_name, player_name, 'value', card.value, i)
        #                     return ('hint', player_name, hint_value[3])
        #                 if my_knowledge.table_cards[card.color] < card.value: # player has a next card for that color
        #                     hint_value = (my_knowledge.my_name, player_name, 'value', card.value, i)
        #                     return ('hint', player_name, hint_value[3])

        #             next_player_idx = (next_player_idx + 1) % my_knowledge.num_players

        #         next_player_idx = (my_knowledge.my_turn_idx + 1) % my_knowledge.num_players #all cards of all players are useless also for the future, suggest to DISCARD
        #         for _ in range(my_knowledge.num_players-1): #for all the other players
        #             player_name = my_knowledge.idx_player[next_player_idx]
        #             player_cards = my_knowledge.players[player_name]['cards']
        #             for i, card in enumerate(player_cards): #for all player's cards
        #                 hint_value = (my_knowledge.my_name, player_name, 'value', card.value, i)
        #                 hint_color = (my_knowledge.my_name, player_name, 'color', card.color, i)
        #                 ## Give a hint that touches more cards
        #                 if compare_hints(hint_value, hint_color) == 0: # hint on value touches more cards (to be discarded)
        #                         return ('hint', player_name, hint_color[3])
        #                 else: # hint on color touches more cards (to be discarded)
        #                         return ('hint', player_name, hint_value[3])
        #             next_player_idx = (next_player_idx + 1) % my_knowledge.num_players
        # if my_knowledge.blue_tokens > 0:
        #     print("\nLAST CASE!\n")
        #     next_player_idx = (my_knowledge.my_turn_idx + 1) % my_knowledge.num_players #try to suggest to KEEP A CARD for later
        #     for _ in range(my_knowledge.num_players-1): #for all the other players
        #         player_name = my_knowledge.idx_player[next_player_idx]
        #         player_cards = my_knowledge.players[player_name]['cards']
        #         for i, card in enumerate(player_cards): #for all player's cards
        #             if last_remaining(card):
        #                 hint_value = (my_knowledge.my_name, player_name, 'value', card.value, i)
        #                 return ('hint', player_name, hint_value[3])
        #         next_player_idx = (next_player_idx + 1) % my_knowledge.num_players


        """ ## Using the q-table (that is being updated constantly) to choose an action as a last resort 
        a = np.argmax(self.q_table[self.state])
        if a == 1 and self.info['blue_tokens'] == 0:
            a = 0
        if a == 0 and self.info['blue_tokens'] == 8:
            a = 1

        if a == 0:
            ## discard
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
        for i, card in enumerate(my_knowledge.my_cards):
            if card[0] != None or card[1] != None:
                my_knowledge.my_cards[i] = (my_knowledge.my_cards[i][0], my_knowledge.my_cards[i][1], my_knowledge.my_cards[i][2] + 1) #update age of each hinted card
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
    global update
    global before_action
    while run:
        if status != "Lobby":
            if my_knowledge.init is not True: 
                s.send(GameData.ClientGetGameStateRequest(playerName).serialize())
            while my_knowledge.my_turn == False:
                time.sleep(sleeptime)
                if update and run:
                    s.send(GameData.ClientGetGameStateRequest(playerName).serialize())
                pass
            update = False
            my_knowledge.my_turn = False
            s.send(GameData.ClientGetGameStateRequest(playerName).serialize()) #like "show" command in client.py, it gives the actual knowledge for the actual player
            before_action = True
            action = select_action()
            command = action_to_command(action)
            if True: # if verbose_action:
                print(command)
            if debug:
                tmp = input() #for debugging
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
            if (data.currentPlayer == playerName and update) or not my_knowledge.init:
                set_knowledge(data)


        if type(data) is GameData.ServerActionInvalid:
            dataOk = True
            print("Invalid action performed. Reason:")
            print(data.message)

        if type(data) is GameData.ServerActionValid: #discard feedback
            dataOk = True
            print(f"Discard action valid! Player {data.lastPlayer} discarded ({data.card.color}, {data.card.value})")
            print("Current player: " + data.player)
            discard_update(data)
            update = True

        if type(data) is GameData.ServerPlayerMoveOk: #good play feedback
            dataOk = True
            print(f"Nice move! Player {data.lastPlayer} played ({data.card.color}, {data.card.value})")
            print("Current player: " + data.player)
            niceMove_update(data)
            update = True

        if type(data) is GameData.ServerPlayerThunderStrike: #bad play feedback
            dataOk = True
            print(f"OH NO! The Gods are unhappy with you! Player {data.lastPlayer} tried to play ({data.card.color}, {data.card.value})")
            badMove_update(data)
            update = True

        if type(data) is GameData.ClientHintData: #hint given from this agent
            dataOk = True
            set_new_hint(data)
            print("Hint type: " + data.type)
            print(f"From player {data.source}")
            print("\tPlayer " + data.destination + " cards with value " + str(data.value) + " are:")
            for i in data.positions:
                print("\t\t" + str(i))
            update = True

        if type(data) is GameData.ServerHintData: #hint given to this agent
            dataOk = True
            set_new_hint(data)
            print("Hint type: " + data.type)
            print(f"From player {data.source}")
            print("\tPlayer " + data.destination + " cards with value " + str(data.value) + " are:")
            for i in data.positions:
                print("\t\t" + str(i))
            update = True

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
            game_over(data.score)

        if not dataOk:
            print("Unknown or unimplemented data type: " +  str(type(data)))

        if hasattr(data, 'currentPlayer') and data.currentPlayer == playerName and before_action:
            print("[" + playerName + " - " + status + "]: ", end="")
            before_action = False
        stdout.flush()