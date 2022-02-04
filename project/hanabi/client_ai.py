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
import numpy as np


if len(argv) < 5:
    print("You need the player name to start the game.")
    print("You need to specify if you want out results in a file (True/False).")
    #exit(-1)
    playerName = "Test" # For debug
    ip = HOST
    port = PORT
    results = True
    num_games_limit = 2
    training = False
else:
    playerName = argv[3]
    ip = argv[1]
    port = int(argv[2])
    results = argv[4] == "True"
    num_games_limit = int(argv[5])
    training = argv[6] == "True"

run = True

debug = False

verbose = False

loaded = True

q_learn = True

statuses = ["Lobby", "Game", "GameHint"]

status = statuses[0]

card_colors = ['red', 'green', 'blue', 'yellow', 'white']

hintState = ("", "")

num_games = 0
average_score = 0.0

update = True
sleeptime = 0.05
before_action = True

my_knowledge = Knowledge(playerName) # all agent knowledge is here

def set_knowledge(data):
    global my_knowledge
    if my_knowledge.init is False: #init Info
        if hasattr(my_knowledge, 'agent'):
            agent = my_knowledge.agent
            my_knowledge = Knowledge(playerName,data,loaded_learn_qTable=loaded,training=training)
            my_knowledge.agent = agent # continue to use the same agent
        else:
            my_knowledge = Knowledge(playerName,data,loaded_learn_qTable=loaded,training=training) #very first init
        if verbose:
            print("Q-Table:")
            print(my_knowledge.agent.q_table)
    else:
        my_knowledge.updateKnowledge(data)
    time.sleep(sleeptime)
    if data.currentPlayer == playerName and update:
            my_knowledge.my_turn = True
            if verbose:
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
    
    # Q-Learning
    if my_knowledge.table_cards[data.card.color] >= data.card.value: #reward
            reward = 8 # discarding this card was useful
    elif data.card.value == 1 and my_knowledge.discard_pile[data.card.color][data.card.value]+1 == 3:
        reward = -7 # this was last '1' card
    elif data.card.value in [2,3,4] and my_knowledge.discard_pile[data.card.color][data.card.value]+1 == 2:
        reward = -6 # this was last '2' card
    elif data.card.value==5 and my_knowledge.discard_pile[data.card.color][data.card.value]+1 == 1:
        reward = -5 # this was last '3' card
    else:
        reward = 9 - my_knowledge.blue_tokens # we have discarded but we could hint

    next_state = my_knowledge.next_state()
    if next_state not in my_knowledge.agent.q_table:
        my_knowledge.agent.q_table[next_state] = np.zeros(len(my_knowledge.actions),dtype=float) # add new state
    ## Update the Q-Table
    my_knowledge.agent.update_q_table(my_knowledge.state,'discard',next_state,reward,False)
    my_knowledge.state = next_state

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

    # Q-Learning
    reward = 10. #reward
    next_state = my_knowledge.next_state()
    if next_state not in my_knowledge.agent.q_table:
        my_knowledge.agent.q_table[next_state] = np.zeros(len(my_knowledge.actions),dtype=float) # add new state
    ## Update the Q-Table
    my_knowledge.agent.update_q_table(my_knowledge.state,'play',next_state,reward,False)
    my_knowledge.state = next_state

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

    # Q-Learning
    reward = -20. #reward
    next_state = my_knowledge.next_state()
    if next_state not in my_knowledge.agent.q_table:
        my_knowledge.agent.q_table[next_state] = np.zeros(len(my_knowledge.actions),dtype=float) # add new state
    ## Update the Q-Table
    my_knowledge.agent.update_q_table(my_knowledge.state,'play',next_state,reward,False)
    my_knowledge.state = next_state

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

    
    # Q-Learning
    reward = my_knowledge.blue_tokens - my_knowledge.num_players #reward: it's better have more blue tokens if possible
    next_state = my_knowledge.next_state()
    if next_state not in my_knowledge.agent.q_table:
        my_knowledge.agent.q_table[next_state] = np.zeros(len(my_knowledge.actions),dtype=float) # add new state
    ## Update the Q-Table
    my_knowledge.agent.update_q_table(my_knowledge.state,'hint',next_state,reward,False)
    my_knowledge.state = next_state

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

    # Q-Learning
    # Computing reward
    if score == 0:
        reward = -50 # penalize lost games
    else:
        reward = score
    # Updating Q-Table
    next_state = (0, 0, 0, 0, 0) # reset state
    my_knowledge.agent.update_q_table(my_knowledge.state,'play',next_state,reward,is_terminal=True) #terminal action - any action is valid
    my_knowledge.state = next_state
    
    if results:
        if num_games == 0: 
            mode = "w"
        else:
            mode = "a"
        if q_learn:
            filename = f"results_{my_knowledge.num_players}_qLearn.txt"
        else:
            filename = f"results_{my_knowledge.num_players}.txt"
        with open(filename, mode) as file_out:
            file_out.write(f"Game n.{num_games}: {score} \n")

    num_games += 1
    average_score = (average_score * (num_games-1)+score)/num_games
    print(f"Games played so far: {num_games}. Actual average score: {average_score}")

    if num_games_limit != None:
        if num_games >= num_games_limit:
            run = False
            print("Log out")
            if results:
                with open(filename, "a") as file_out:
                    file_out.write(f"----------------------------\n")
                    file_out.write(f"Avarage score: {average_score}\n")
            my_knowledge.agent.save_learned_model(f"learned_qTable_{my_knowledge.num_players}.npy")
            os._exit(0)
        else:
            print("Beginning a new game...")
            update = True
            before_action = True
            agent = my_knowledge.agent
            my_knowledge = Knowledge(playerName) #reset info
            my_knowledge.agent = agent # continue to use the same agent

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

        ## Last round (play the newest card if we have more than one storm tokens available)
        if my_knowledge.last_round:
            if my_knowledge.red_tokens > 1 and my_knowledge.num_deck_cards > 0:
                return ('play', my_knowledge.handSize -1 )

        # Play rules with hints 
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
                # Hint dangerous cases
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

        if q_learn:
            # Q-Learning
            print("Q-Learning action")
            action = my_knowledge.agent.pick_action(my_knowledge.state)
            if action == "hint" and my_knowledge.blue_tokens == 0: # you cannot pick this action
                action = "discard"
            if action == "discard" and my_knowledge.blue_tokens == 8: # you cannot pick this action
                action = "hint"

            if action == "discard":
                # discard action
                for idx, card in enumerate(my_knowledge.my_cards):
                    if card[0] == None and card[1] == None: #totally unclued
                        return ("discard", idx)
                for idx, card in enumerate(my_knowledge.my_cards):
                    if card[0] == None or card[1] == None:
                        return ("discard", idx) #partially unclued
                return ("discard", 0) #discard the oldest

            if action == "hint":
                # hint action to further plpayer respect to me
                if my_knowledge.my_turn_idx == 0:
                    furthest_player_idx = my_knowledge.num_players-1
                else:
                    furthest_player_idx = my_knowledge.my_turn_idx-1
                player_name = my_knowledge.idx_player[furthest_player_idx]
                player_cards = my_knowledge.players[player_name]['cards']
                #try to suggest to KEEP A CARD for later
                for i, card in enumerate(player_cards): #for all player's cards
                    if my_knowledge.table_cards[card.color] < card.value: # player has a next card for that color
                        hint_value = (my_knowledge.my_name, player_name, 'value', card.value, i)
                        if is_hint_not_misunderstandable(hint_value,card.color):
                            print("KEEP IT")
                            return ('hint', player_name, hint_value[3])
                #all cards of all players are useless also for the future, suggest to DISCARD
                for i, card in enumerate(player_cards): #for all player's cards
                    hint_value = (my_knowledge.my_name, player_name, 'value', card.value, i)
                    hint_color = (my_knowledge.my_name, player_name, 'color', card.color, i)
                    print("DISCARD IT")
                    ## Give a hint that touches more cards
                    if compare_hints(hint_value, hint_color) == 0: # hint on color touches more cards (to be discarded)
                            return ('hint', player_name, hint_color[3])
                    else: # hint on value touches more cards (to be discarded)
                            return ('hint', player_name, hint_value[3])

            if action == "play":
                ## Play your newest card
                return ("play", my_knowledge.handSize - 1) 

        else:  #Q-Learning disabled
            print("Rule-based last resource")
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
            time.sleep(sleeptime)
            set_new_hint(data)
            print("Hint type: " + data.type)
            print(f"From player {data.source}")
            print("\tPlayer " + data.destination + " cards with value " + str(data.value) + " are:")
            for i in data.positions:
                print("\t\t" + str(i))
            update = True

        if type(data) is GameData.ServerHintData: #hint given to this agent
            dataOk = True
            time.sleep(sleeptime)
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