import random, logging
logging.basicConfig(filename='example.log',level=logging.DEBUG)

class Board:
    def __init__(self, gameid, db):
        logging.debug("Board.__init__ called")
        # set empty state
        self.state = ["-","-","-","-","-","-","-","-","-"]
        self.gameid = gameid
        self.db = db

        # populate with previous moves
        self.setState()

    
    # O for player, X for phynd

    def getState(self):
        return self.state

    def getGameId(self):
        return self.gameid

    def prepScenario(self):
        logging.debug("Board.prepScenario called")
        ### check if scenario is already in db
        row = self.db.execute('select count(*) from weights where scenario=?', [self.stateToScenario()]).fetchone()
        logging.debug("board.prepscenario found " + str(row[0]))
        if(row[0] < 1):
            self.initScenario()
        return

    def setState(self):
        logging.debug("board.setState called")
        # get from db
        moves = self.db.execute('select isHuman, position from moves where gameid=? order by moveid asc', [str(self.gameid)]).fetchall()
        #convert
        for move in moves:
            if (move['isHuman']):
                indicator = "O"
            else:
                indicator = "X"
            self.state[move['position']] = indicator
        logging.debug("new state after setState: " + str(self.state))
        return

    def stateToScenario(self):
        logging.debug("Board.stateToScenario called, board size " + str(len(self.state)) + " " + str(self.state))
        # convert state to db format
        scenario = ""
        for character in self.state:
            scenario += character.upper()
        logging.debug("Board.stateToScenario generated " + scenario)
        return str(scenario)

    def initScenario(self):
        logging.debug("Board.initScenario called")
        ### initialize db rows for scenario
        # generate possible moves
        moves = self.findPlayableSlots()
        default_weight = 5
        # store to db
        for move in moves:
            self.db.execute('insert into weights values (?, ?, ?)', (self.stateToScenario(), move, default_weight))
        return

    def findPlayableSlots(self):
        logging.debug("Board.findPlayableSlots called")
        # get a list of spots that are legal moves
        moves = []
        for counter, character in enumerate(self.state):
            if(character == "-"):
                moves.append(counter)
        logging.debug("Board.findPlayableSlots found " + str(moves))
        return moves

    def recordInput(self, entity, position):
        logging.debug("Board.recordInput called")
        self.state[position] = entity
        if(entity.upper() == 'O'):
            human = 1
        else:
            human = 0
        # get last move from game
        lastMove = self.db.execute('select max(moveid) from moves where gameid=?', [str(self.gameid)]).fetchone()
        logging.debug("last move = " + str(lastMove[0]))
        if(lastMove[0] is not None):
            move = lastMove[0] + 1
        else:
            move = 0
        # double-check that that tile is not already occupied
        if (position in self.findPlayableSlots()):
            # record a move to db
            logging.debug("adding " + str(move) + " " + str(self.gameid) + " " + str(human) + " " + str(position) + " to db.")
            self.db.execute('insert into moves values (?, ?, ?, ?)', (move, str(self.gameid), bool(human), position))
        return

    def getMlWeights(self):
        logging.debug("Board.getMlWeights called")
        # get response weights from db
        rows = self.db.execute('select position, weight from weights where scenario=? and weight > 0', self.stateToScenario()).fetchAll()
        return rows

    def chooseResponse(self):
        logging.debug("Board.chooseResponse called")
        ### choose a response based on weights
        # get weights
        rows = self.getMlWeights()
        # get sum of weights
        totalWeight = 0.00
        for row in rows:
            totalWeight += row['weight']
        # generate random number in sum range
        target = totalWeight * random.random()
        totalWeight = 0.00
        # assign response
        position = 0
        for row in rows:
            totalWeight += row['weight']
            if(totalWeight > target):
                move = row['position']
        return position

    def isPlayable(self):
        logging.debug("Board.isPlayable called")
        ### determine if game is in a state where a move can be made
        # check if board is full
        flag = True
        if(self.findPlayableSlots() == 0):
            flag = False
        else:
            ## todo: add game logic
            if(self.hasWon('X') or self.hasWon('O')):
                flag = False
        return flag

    def hasWon(self, entity):
        logging.debug("Board.hasWon called")
        flag = False
        ### check if an entity has won the game
        
        for i in range(0,3):
            rsize = 3
            # scan horizontally
            xscan = 0 + (rsize * i)
            if ((self.state[xscan] == entity and self.state[xscan + 1] == entity) and self.state[xscan + 2] == entity):
                flag = True
            # scan vertically
            if ((self.state[i] == entity and self.state[i + rsize] == entity) and self.state[i + (2 * rsize)] == entity):
                flag = True
        #check diagonals
        if ((self.state[0] == entity and self.state[rsize + 1] == entity) and self.state[2 * (rsize + 1)] == entity):
            flag = True
        if ((self.state[rsize - 1] == entity and self.state[2 * (rsize - 1)] == entity) and self.state[3 * (rsize - 1)] == entity):
            flag = True
        return flag

    def updateMlWeights(self):
        logging.debug("Board.udpateMlWeights called")
        # update weights of moves at the end of a game based on winnings
        return