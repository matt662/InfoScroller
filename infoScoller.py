'''
Created on Sep 28, 2017

@author: Matt
'''

import googlemaps
import sys
from time import sleep
from time import time as timetime
from datetime import datetime, time
import threading
import twitter
import queue
import ldp
import fontv
import logging
import traceback
import pychromecast
from ConfigParser import SafeConfigParser

parser = SafeConfigParser()
parser.read('config.ini')


logging.basicConfig(level=logging.INFO)
messageQueue = queue.Queue()

gmaps = googlemaps.Client(key=parser.get('google_maps', 'key'))
START_ADDRESS = key=parser.get('google_maps', 'start_address')
END_ADDRESS = key=parser.get('google_maps', 'end_address')


ACCESS_TOKEN = key=parser.get('twitter', 'access_token')
ACCESS_SECRET = key=parser.get('twitter', 'access_secret')
CONSUMER_KEY = key=parser.get('twitter', 'consumer_key')
CONSUMER_SECRET = key=parser.get('twitter', 'consumer_secret')


twitterapi = twitter.Api(consumer_key=CONSUMER_KEY,
  consumer_secret=CONSUMER_SECRET,
    access_token_key=ACCESS_TOKEN,
    access_token_secret=ACCESS_SECRET)

interrupt = False

class data_fetcher(threading.Thread):
    
    def __init__ (self,q):
        self.q = q
        threading.Thread.__init__(self,name='data_fetching_thread')
    
    def run(self):
        global interrupt
        while not interrupt:
            try:
                logging.debug('interrupt fetch=' + str(interrupt))
                nowTime=datetime.now()
                directions_result= gmaps.directions(START_ADDRESS, END_ADDRESS,avoid="tolls", departure_time=nowTime)
                duration = directions_result[0]["legs"][0]["duration_in_traffic"]["text"]
                summary = directions_result[0]['summary']
                mention = duration + ' ' + summary
                message = {'travel': {'time': duration, 'summary': summary, 'seconds': directions_result[0]["legs"][0]["duration_in_traffic"]['value']}}
                self.q.put(message)
                logging.info('Time to work: ' + mention)
            except(googlemaps.exceptions.ApiError, googlemaps.exceptions.HTTPError, googlemaps.exceptions.Timeout, googlemaps.exceptions.TransportError):
                logging.warn('Maps Error')
            except:
                logging.warn('General Maps Error')
            try:
                pass #place holder for future twitter fetching
            except(twitter.error.TwitterError):
                logging.warn
            except:
                logging.warn('General Error on Twitter Fetch')
                traceback.print_exc()
            for i in range(60):
                if interrupt:
                    logging.info('end received for fetch')
                    break
                sleep(1)
                
class cast_fetcher(threading.Thread):
    
    def __init__ (self,q):
        self.q = q
        threading.Thread.__init__(self,name='chromecast_thread')
    
    def run(self):
        global interrupt
        chromecasts = pychromecast.get_chromecasts()
        while not interrupt:
            try:
                for cc in chromecasts:
                    if cc.media_controller.status.player_is_playing:
                        if cc.media_controller.status.artist and cc.media_controller.status.title:
                            message = {'now_playing': {'artist': cc.media_controller.status.artist, 'title': cc.media_controller.status.title}}
                        else:
                            message = {'now_playing': {'title': cc.media_controller.status.title}}
                        logging.info('added message for chromecast')
                        self.q.put(message)
            except:
                logging.warn('General Error on Chromecast Fetch')
                traceback.print_exc()
            for i in range(10):
                if interrupt:
                    logging.info('end received for chrome fetch')
                    break
                sleep(1)
class matrixPrinter(threading.Thread):
    
    def __init__ (self,q):
        self.q = q
        ldp.init()
        self.displaywidth=80
        self.totalwidth=0
        threading.Thread.__init__(self,name='matrix_Printer_thread')
    
    def run(self):
        global interrupt
        previousMessage = None
        travel = None
        while not interrupt:
            currentMessage = None
            logging.debug('interrupt matrix=' + str(interrupt))
            if not self.q.empty():
                previousMessage = self.q.get()
                currentMessage = previousMessage
                if 'travel' in previousMessage:
                    travel = previousMessage['travel']
            if travel is not None:
                if (time(7,30) <= datetime.now().time() <= time(9,0)) and (datetime.now().isoweekday() in range(1,6)):
                    text = 'Drive: ' + travel['time']
                    logging.info(text)
                    value = travel['seconds']
                    if value < 1800:
                        color = 2
                    elif value >= 1800 and value < 2400:
                        color = 3
                    else:
                        color = 1
                    self.updatestaticmatrix(text,color,5)
                    self.updatestaticmatrix('via', color, 2)
                    self.updatescrollmatrix(travel['summary'], color, 0.006, 2)
            if currentMessage is not None and 'now_playing' in previousMessage:
                now_playing = '>Now Playing: ' + previousMessage['now_playing']['title']
                if 'artist' in previousMessage['now_playing']:
                    now_playing += ' >By: ' + previousMessage['now_playing']['artist']
                color = 2
                logging.info(now_playing)
                self.updatescrollmatrix(now_playing, color, 0.006, 2)
            ldp.clear()
                

    # the matrix is a representation of the led's that are lit on the 80x8 display
    #
    # matrix=[[0 for i in xrange(80)] for i in xrange(8)]
    #
    # function to shift left all the vaules of the matrix array
    # this allows us to put new data in the first column
    #
    def shiftmatrix(self, matrix):
        for row in range(8):
            for col in range(79,0,-1):
                matrix[row][col]=matrix[row][col-1]
    # end def
    
    # function to read the matrix array and output the values to the display device
    #
    def showscrollmatrix(self, matrix):
        #ldp.displayoff()
        for row in reversed(range(8)):
            for col in reversed(range(80)):
                ldp.colourshift(matrix[row][col])
            ldp.showrow(row)
    # end def
    
    # function to read the matrix array and output the values to the display device
    #
    def showstaticmatrix(self, matrix):
        for row in range(8):
            for col in range(80):
                ldp.colourshift(matrix[row][col])
            ldp.showrow(row)
    # end def
    
    #
    # Main
    #
    # initialise the display
    #

    #
    # assign the command line args for the text and colour
    #
    
    # dotarray is  8 X n
    # n is determined by the number of characters multiplyed by 8 
    # n will be len(dotarray[0]) after filling dotarray from characters
    # in the inputarray
    #
    
    #textinput=str(sys.argv[1])
    #colour=int(sys.argv[2])
    
    def updatescrollmatrix(self, textinput, colour, move_sec, hold_sec):
        global interrupt
        matrix=[[0 for i in xrange(80)] for i in xrange(8)]
        dotarray=[[] for i in xrange(8)]
        
        # append extra characters to text input to allow for wrap-around
        #textinput+='  ::  '
        
        # save the ascii values of the input characters into the inputarray 
        # the font module uses the ascii value to index the font array
        inputarray=[]
        for char in textinput:
            inputarray.append(ord(char))
        #
        # fill the dot array with the colour digits
        # this is the dot pattern that we want to show
        #
        for row in range(8):
            for ascii in inputarray:
                # get the width of the character from the first element of the font variable
                width=fontv.array[ascii][0]
                #get the binary representation of the charatcter at that row
                binary='{0:{fill}{align}{width}{base}}'.format(fontv.array[ascii][row+1],base='b',fill='0',align='>',width=width)
                #Go through each bit in binary and add it to the row as either off for 0 or color for 1
                for digit in range(width):
                    if binary[digit] == '0':
                        dotarray[row].append(0)
                    else:
                        dotarray[row].append(colour)
    
        # loop around each column in the dotarray
        for col in range(len(dotarray[0])):
            for row in range(8):
                # copy the current dotarray column values to the first column in the matrix
                matrix[row][0]=(dotarray[row][col])
            # now that we have updated the matrix lets show it
            timeout = timetime() + move_sec    
            while not interrupt:
                self.showscrollmatrix(matrix)
                if timetime() > timeout:
                    break
            # shift the matrix left ready for the next column
            self.shiftmatrix(matrix)    
            
        timeout = timetime() + hold_sec    
        while not interrupt:
            self.showscrollmatrix(matrix)
            if timetime() > timeout:
                break
    
    def updatestaticmatrix(self, textinput, colour, hold_sec):
        global interrupt
        matrix=[[0 for i in xrange(80)] for i in xrange(8)]
        # save the ascii values of the input characters into the inputarray 
        # the font module uses the ascii value to index the font array
        inputarray=[]
        for char in textinput:
            inputarray.append(ord(char))
        
        # dotarray is  8 X n
        # n is determined by the number of characters multiplyed by 8 
        # n will be len(dotarray[0]) after filling dotarray from characters
        # in the inputarray
        #
        dotarray=[[] for i in xrange(8)]
        #
        # fill the dot array with the colour digits
        # this is the dot pattern that we want to show
        #
        for row in range(8):
            for ascii in inputarray:
                # get the width of the character from the first element of the font variable
                width=fontv.array[ascii][0]
                binary='{0:{fill}{align}{width}{base}}'.format(fontv.array[ascii][row+1],base='b',fill='0',align='>',width=width)
                for digit in range(width):
                    if binary[digit] == '0':
                        dotarray[row].append(0)
                    else:
                        dotarray[row].append(colour)
        
        totalwidth=len(dotarray[0])
        if totalwidth > self.displaywidth:
            logging.warn('Message is Larger than the Display')
            return
        
        offset=int((self.displaywidth - totalwidth) / 2)
        
        # Fill the matrix initially with offset spaces to centre align the message
        #
        for col in range(offset):
            for row in range(8):
                matrix[row][col]=0
        # now fill the rest of the matrix with the dotarray
        for col in range(totalwidth):
            for row in range(8):
                # copy the current dotarray column values to the first column in the matrix
                matrix[row][offset+col]=(dotarray[row][col])
        
        timeout = timetime() + hold_sec        
        while not interrupt:
            self.showstaticmatrix(matrix)
            if timetime() > timeout:
                break    
        return matrix    
    
    def showstaticmatrixfortime(self, matrix, t):
        global interrupt
        timeout = timetime() + t
        while not interrupt:
            self.showstaticmatrix(matrix)
            if timetime() > timeout:
                break

def main():
    global interrupt  
    fetcherThread = data_fetcher(messageQueue)
    fetcherThread.daemon=True
    fetcherThread.start()
    printerThread = matrixPrinter(messageQueue)
    printerThread.daemon=True
    printerThread.start()
    castThread = cast_fetcher(messageQueue)
    castThread.daemon=True
    castThread.start()
    logging.debug('Threads Started')
    try:
        while True:
            sleep(.1)
    except KeyboardInterrupt:
        logging.info('Shutdown requested... exiting')
        interrupt = True
        fetcherThread.join()
        printerThread.join()

if __name__ == "__main__":
    logging.debug(sys.version)
    main()
    ldp.clear()
    logging.debug('main ended')
    
