import logging
import socketIO_client
from socketIO_client.transports import get_response
from socketIO_client.parsers import get_byte, _read_packet_text, parse_packet_text

from requests.exceptions import ConnectionError

#Custom import
import sys
import datetime
from CryptocurrencyExchanges import get_exchanges
import pandas as pd
import time

import psycopg2

# MODIFY EVERYTHING TO WORK WITH POSTGRESQL
# MAKE CODE BROADCAST THE CANDLES THROUGH A SOCKET SO THE OTHER SCRIPTS CAN CONNECT TO IT AND RECEIVE THEM

# TODO:
# Move login credentials elsewhere
# Finish testing
# Calculate buy/sell force for each minute bar
# Add Documentation
# Refactor code to remove globals


# WebSocket Debugging
logging.getLogger('requests').setLevel(logging.DEBUG)

#global start_time
start_time = datetime.datetime.now()

#### CLASSES ####

class Queue(object):
  # Queue keeps a list of received Trades and remembers what minute they occured in
  # when it receives a Trade from the next minute it calculates the ohlcv values for 
  # the previous minute and uploads them to the db

  def __init__(self, symbol, cursor, connection):
    self.min = 0
    self.time = 0
    self.queue = []
    self.symbol = symbol
    self.cursor = cursor
    self.connection = connection

  def add_trade(self, trade):
    if isinstance(trade, Trade):
      if len(self.queue)==0:
        # If queue is empty create queue with current Trade
        # and set the minute + time to those of the added trade
        self.queue += [trade.get_trade()]
        self.min = int(trade.trade_time.minute)
        self.time = trade.trade_time
      else:
        cur_min = int(trade.trade_time.minute)
        if cur_min == self.min:
          # If current trade is in the same minute as the previous, add it to the queue
          self.queue += [trade.get_trade()]
          self.time = trade.trade_time
        else:
          if trade.trade_time > self.time:
            # If trades occur in different minutes and the new trade's datetime is bigger than our queue's
            # Calculate ohlcv and start next queue
            self.calculate_ohlcv()
            self.min = cur_min
            self.time = trade.trade_time
            self.queue = [trade.get_trade()]

  def calculate_ohlcv(self):
    # This function uses pandas resample to calculate ohlcv values for the saved minute queue and uploads them to db
    if len(self.queue) > 0:
      df = pd.DataFrame(self.queue)
      df.set_index('date', inplace=True)
      bars = df.price.resample('60s').ohlc()
      bars.fillna(method='ffill', inplace=True)
      vol = df.volume.resample('60s').sum()
      ohlcv = bars.join(vol)
      logging.debug (self.symbol, ohlcv)

      write_to_postgresql(self.cursor, self.connection, self.symbol, ohlcv)

class Trade(object):
    def __init__(self, exchange_name, currency_1, currency_2, flag, trade_time, quantity, price, total):
      self.exchange_name = exchange_name
      self.currency_1 = currency_1
      self.currency_2 = currency_2
      self.trade_time = datetime.datetime.fromtimestamp(int(trade_time))
      self.quantity = float(quantity)
      self.price = float(price)
      self.total = float(total)
      self.trade_types = [None, "Sell", "Buy", None, "Unknown"]
      self.trade_type = self.trade_types[int(flag)]
    
    def __str__(self):
      """Overrides the default implementation"""
      # Trade's string form
      ret_str = self.exchange_name+" "+self.trade_time.strftime('%Y-%m-%d %H:%M:%S')+" --> "
      ret_str += self.currency_1+" "+self.trade_type+" "+str(self.price)+"€ - "+str(self.quantity)+"BTC ("+str(self.price)+"€)"
      return ret_str
    
    def get_trade(self):
      return {'date':self.trade_time, 'symbol':self.currency_1, 'price':self.price, 'volume':self.quantity}

    def __eq__(self, other):
      """Overrides the default implementation"""
      # Method used to compare trades
      if isinstance(self, other.__class__):
          return self.__dict__ == other.__dict__
      return False

#### FUNCTIONS ####
  
def on_message(*args):
  # Websocket message received
  global queues
  global start_time
  add_message_to_queue(queues, start_time, args[0])

def on_connect():
  # Websocket connected
  logging.debug (datetime.datetime.now(), "[Connected]")

def on_disconnect():
  # Websocket disconnected
  logging.debug(datetime.datetime.now(),"[Disconnected]")

  time.sleep(10)
  start('all')

def add_message_to_queue(queues, start_time, args):
  # Converts msg args into Trades and adds them to their respective queues
  trade_msg = convert_message_to_trade(start_time, args)
  if trade_msg != None:
    queues[trade_msg.currency_1].add_trade(trade_msg)


def convert_message_to_trade(start_time, msg):
  # Converts msg args into Trades
  msg_parts = msg.decode()[7:-2].split("~")
  if len(msg_parts)>=9:
    if int(msg_parts[0]) == 0:
      trade = Trade(msg_parts[1], msg_parts[2], 
        msg_parts[3], msg_parts[4], msg_parts[6], 
        msg_parts[7], msg_parts[8], msg_parts[9])
      if trade.trade_time > start_time:
        return trade

def init_postgresql():
  cons = "dbname='ohlcv' user='juan' host='postgresql-db' password='ijosdeputa2'"
  try:
    conn = psycopg2.connect(cons)
    cur = conn.cursor()
  except:
    raise ConnectionError("Unable to connect to the database")
  return cur, conn

def write_to_postgresql(cursor, connection, symbol, ohlcv):
  try:
    names = {'BTC':'bitcoin', 'ETH':'ethereum', 'XRP':'xrp', 'EOS':'eos', 'LTC':'litecoin'}
    SQL = "INSERT INTO "+names[symbol]+" (date, open, high, low, close, volume) VALUES (%s, %s, %s, %s, %s, %s)"
    data = (ohlcv.index[0], ohlcv.open[0], ohlcv.high[0], ohlcv.low[0], ohlcv.close[0], ohlcv.volume[0], )
    cursor.execute(SQL, data)
    connection.commit()
  except:
    connection.rollback()


"""---- Extra functions to support XHR1 style protocol ----"""
def _new_read_packet_length(content, content_index):
  # Extra function - IGNORE, DON'T DELETE
  packet_length_string = ''
  while get_byte(content, content_index) != ord(':'):
    byte = get_byte(content, content_index)
    packet_length_string += chr(byte)
    content_index += 1
  content_index += 1
  return content_index, int(packet_length_string)

def new_decode_engineIO_content(content):
  # Extra function - IGNORE, DON'T DELETE
  content_index = 0
  content_length = len(content)
  while content_index < content_length:
    try:
      content_index, packet_length = _new_read_packet_length(content, content_index)
    except IndexError:
      break
    content_index, packet_text = _read_packet_text(content, content_index, packet_length)
    engineIO_packet_type, engineIO_packet_data = parse_packet_text(packet_text)
    yield engineIO_packet_type, engineIO_packet_data

def new_recv_packet(self):
  # Extra function - IGNORE, DON'T DELETE
  params = dict(self._params)
  params['t'] = self._get_timestamp()
  response = get_response(
    self.http_session.get,
    self._http_url,
    params=params,
    **self._kw_get)
  for engineIO_packet in new_decode_engineIO_content(response.content):
    engineIO_packet_type, engineIO_packet_data = engineIO_packet
    yield engineIO_packet_type, engineIO_packet_data

"""---- End extra functions ----"""

def start(symbol):
  # Starts websocket with 'symbol' exchanges
  global queues
  logging.debug ("Websocket Starting...")
  setattr(socketIO_client.transports.XHR_PollingTransport, 'recv_packet', new_recv_packet)
  logging.basicConfig(filename='debug.log',level=logging.DEBUG)
  try:
    socket_exchanges, coin_list = get_exchanges(symbol)

    cursor, connection = init_postgresql()
    queues = {x:Queue(x, cursor, connection) for x in coin_list}
    socket = socketIO_client.SocketIO('https://streamer.cryptocompare.com')
    socket.on('message', on_message)
    socket.on('disconnect', on_disconnect)
    socket.on('connect', on_connect)
    socket.emit('SubAdd', { 'subs': socket_exchanges});
    socket.wait()
  except ConnectionError:
    logging.debug('The server is down. Try again later.')
  except IndexError:
    time.sleep(10)
    start(symbol)
  except (KeyboardInterrupt, SystemExit):
    logging.debug ("(",datetime.datetime.now(),") Unsubscribing...")
    socket.emit('SubRemove', {'subs':socket_exchanges});
    socket.wait(seconds=1)
    cursor.close()
    conn.close()
    logging.debug ("(",datetime.datetime.now(),") Websocket exiting...")
    sys.exit(0)

if __name__ == '__main__':
  start('all')