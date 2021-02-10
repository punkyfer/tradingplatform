import CryptoCompareWebSocketOHLCV as cws
import unittest
from io import StringIO
from unittest import mock
import datetime
import pytz

# TODO:
# Add testing for socketio client + start()
# Maybe add tests for backup_logs() + get_date_filename
# Integration tests for DB ???
# Create 'real' Factory for Trades ???


# Class "Factories"
# Trades
def get_timestamp(ts):
  timestamp_list =[1528378700, # 6/7/2018 15:38:20
    1528379718, # 6/7/2018 15:55:18
    1528379731, # 6/7/2018 15:55:31
    1528379772] # 6/7/2018 15:56:12
  
  return timestamp_list[ts]

def create_trade(timestamp=1):
  exchange_name = "BitHouse"
  currency_1 = "BTC" 
  currency_2 = "EUR" 
  flag = 0
  quantity = 1.5 
  price = 6500.88
  total = 10000
  trade_time = get_timestamp(timestamp)
  
  return cws.Trade(exchange_name, currency_1, currency_2, flag, trade_time, quantity, price, total)


# Class Testing
# Queue
class QueueTest(unittest.TestCase):

  def setUp(self):
    self.queue = cws.Queue('BTC', None)

  def test_non_trade(self):
    prev_len = len(self.queue.queue)
    trade = "FOO"
    
    self.queue.add_trade(trade)

    self.assertEqual(prev_len, len(self.queue.queue))

  def test_add_first_trade(self):
    self.queue.queue = []
    trade = create_trade(1)
    
    self.queue.add_trade(trade)

    self.assertEqual(self.queue.queue, [trade.get_trade()])

  def test_add_second_trade(self):
    trade_1 = create_trade(1)
    trade_2 = create_trade(2)

    self.queue.queue = [trade_1.get_trade()]
    self.queue.min = int(trade_1.trade_time.minute)
    self.queue.time = trade_1.trade_time

    self.queue.add_trade(trade_2)

    self.assertEqual(self.queue.queue, [trade_1.get_trade(), trade_2.get_trade()])

  def test_add_previous_trade(self):
    trade_1 = create_trade(1)
    trade_2 = create_trade(0)

    self.queue.queue = [trade_1.get_trade()]
    self.queue.min = int(trade_1.trade_time.minute)
    self.queue.time = trade_1.trade_time

    self.queue.add_trade(trade_2)

    self.assertEqual(self.queue.queue, [trade_1.get_trade()])

  @mock.patch('CryptoCompareWebSocketOHLCV.Queue.calculate_ohlcv')
  def test_add_next_min_trade(self, *args):
    trade_1 = create_trade(1)
    trade_2 = create_trade(3)

    prev_queue = [trade_1.get_trade(), trade_2.get_trade()]
    self.queue.time = trade_1.trade_time
    self.queue.min = int(trade_1.trade_time.minute)
    self.queue.queue = prev_queue
    self.queue.symbol = 'BTC'
    self.queue.db = None
    next_min_trade = create_trade(3)
    self.queue.add_trade(next_min_trade)

    self.queue.calculate_ohlcv.assert_called_once()
    self.assertEqual(self.queue.queue, [next_min_trade.get_trade()])

  @mock.patch('CryptoCompareWebSocketOHLCV.upload_data_arcticdb')
  def test_empty_calculate_ohlcv(self, *args):
    self.queue.queue = []

    self.queue.calculate_ohlcv()

    cws.upload_data_arcticdb.assert_not_called()

  @mock.patch('CryptoCompareWebSocketOHLCV.upload_data_arcticdb')
  def test_calculate_ohlcv(self, *args):
    trade_1 = create_trade(1)
    trade_2 = create_trade(2)

    self.queue.queue = [trade_1.get_trade(), trade_2.get_trade()]
    self.queue.symbol = "BTC"
    self.queue.db = None

    self.queue.calculate_ohlcv()

    cws.upload_data_arcticdb.assert_called_once()


class convert_message_to_trade_test(unittest.TestCase):
  def test_good_message(self):
    msg = b'2["m","0~Coinbase~BTC~EUR~1~14742062~'+bytes(str(get_timestamp(1)), 'utf8')+b'~0.01~6451.61~64.5161~1f"]'

    start_time = datetime.datetime.fromtimestamp(get_timestamp(0)).replace(tzinfo=pytz.UTC)
    processed_msg = cws.to_trade_message(start_time, msg)

    self.assertEqual(processed_msg, cws.Trade('Coinbase','BTC','EUR', 1, get_timestamp(1), 0.01, 6451.61, 64.5161))

  def test_bad_message(self):
    msg = b"FOO"

    start_time = datetime.datetime.fromtimestamp(get_timestamp(0)).replace(tzinfo=pytz.UTC)
    processed_msg = cws.to_trade_message(start_time, msg)

    self.assertEqual(processed_msg, None)

  def test_prev_start_message(self):
    msg = b'2["m","0~Coinbase~BTC~EUR~1~14742062~'+bytes(str(get_timestamp(0)), 'utf8')+b'~0.01~6451.61~64.5161~1f"]'

    start_time = datetime.datetime.fromtimestamp(get_timestamp(3)).replace(tzinfo=pytz.UTC)
    processed_msg = cws.to_trade_message(start_time, msg)

    self.assertEqual(processed_msg, None)