# Hanabi Agent - Computational Intelligence 2021/2022
### Exam of 11th February 2022 - Politecnico di Torino
### Andrea Protopapa - 286302
## The problem
Hanabi is a cooperative game of imperfect information. Players are aware of other players' cards but not their own, and attempt to play a series of cards in a specific order to set off a simulated fireworks show. The types of information that players may give to each other is limited, as is the total amount of information that can be given during the game. In this way, players don't have all the knowledge needed to make a good decision, they work with what they have and trying to infer the rest.

This work requires teaching the client to play the game of Hanabi (rules can be found [here](https://www.spillehulen.dk/media/102616/hanabi-card-game-rules.pdf)).

## First implementation: Rule Based
The first basic idea was to create an hand-coding rule-based strategy. These rules outline triggers and the actions that should follow (or are triggered).

 These rules most often take the form of if statements (```IF outlines the trigger, THEN specifies the action to complete```). 
 They are based on the most principal rules that every player must know to win the game, plus some rules found by experience and some very typical conventions used by the most of the people playing this game. 
 
 It's important to notice that if you tell the machine to do something incorrectly, it will do it incorrectly. In this case, being the game with an imperfect information, we cannot always be sure about our actual state and the best action we can succeed. There are situations where we cannot have the assurance of what is the best action to do (give an hint, discard or play a card). Therefore our rules cannot include all the possible states and have a complete vision on the state domain.
## Add some intelligence: Q-Learning
For these reasons presented, we have introduce some "inteligence" on our agent, so that is more able to adapt to the most uncertain situations but also to play with other different playmates, each one with his personal strategies and conventions.

Q-Learning, that is a model-free Reinforcement Learning algorithm, helps a machine (agent) to learn a behaviour through many "trial-and-error" iterations in an dynamic enviroment.
This interaction between the agent and the enviroment is defined with states, actions and rewards: the actions incluence not only the immediate reward, but also the next states, actions and rewards of the future.

The objective is to maximize the (cumulated) discounted rewards received in the future at each single episode making far-future rewards less prioritized than near-term rewards, selecting in this way its best action.

This type of algorithm helps to learn in an uncertain enviromet like that one of Hanabi, forecasting sequences of decisions.
In our implementation we use tables (Q-Tables) to memorize the state/action values and pick the best action given the actual state.

## How to use it

### Server

The server accepts passing objects provided in GameData.py back and forth to the clients.
Each object has a ```serialize()``` and a ```deserialize(data: str)``` method that must be used to pass the data between server and client.

Watch out! I'd suggest to keep everything in the same folder, since serialization looks dependent on the import path (thanks Paolo Rabino for letting me know).

Server closes when no client is connected.

To start the server:

```bash
python server.py <minNumPlayers>
```

Arguments:

+ minNumPlayers, __optional__: game does not start until a minimum number of player has been reached. Default = 2


Commands for server:

+ exit: exit from the server

### Client
Use this client to play "as a human", against other clients (humans or AI-agents)

To start the client:

```bash
python client.py <IP> <port> <PlayerName>
```

Arguments:

+ IP: IP address of the server (for localhost: 127.0.0.1)
+ port: server TCP port (default: 1024)
+ PlayerName: the name of the player

Commands for client:

+ exit: exit from the game
+ ready: set your status to ready (lobby only)
+ show: show cards
+ hint \<type> \<destinatary> \<value>:
  + type: 'color' or 'value'
  + destinatary: name of the person you want to ask the hint to
  + value: value of the hint
+ discard \<num>: discard the card *num* (\[0-4]) from your hand
+ play \<num>: play the card *num* (\[0-4]) from your hand

### AI - Client
Use this client to start an AI-agent that "plays for you", against other clients (humans or AI-agents). 

To start the client this is the general command:

```bash
python client_ai.py <IP> <port> <PlayerName> <print_results> <n_iterations> <training>
```

Arguments:

+ ```IP```: IP address of the server (for localhost: 127.0.0.1)
+ ```port```: server TCP port (default: 1024)
+ ```PlayerName```: the name of the player
+ ```print_results```: bool - this agent will print the score of each game iteration and the final avarage score in a dedicated .txt file. Make sure to use only one agent using this arguments equals to "True"
+ ```n_iterations```: int - the number of iteration of the game to be played consecutively 
+ ```training```: bool - set the usage mode of the agent, doing also some exploration if you are in 'Training' mode. Set to 'False' to just exploit the results of the Q-Table

An example of usage, to start an AI agent called "Bob" ready to do one iteration of game, is the following:
```bash
python client_ai.py 127.0.0.1 1024 Bob True 1 False
```

Since the project is based on a Q-Learning strategy, we also offer in addition Q-Tables already filled by values of precedent trainings (500 iteration of games for each table). Depending on the number of players, it will be automatically selected the most appropriate Q-Table. If there isn't, it will be created a new one. 

Results show that the most of advantage using Q-Learning in this scenario is with a fewer number of players, since you have more possibilities to "have no idea on what to do".

The system is based on experience, and for this reason with more and more iteration of the game we suppose to obtain better and better results, exploring all the possible states of the enviroment.

