import pymongo
import os
import pandas as pd
from datetime import datetime as dt
from arctic import Arctic
from arctic.auth import Credential
from arctic.hooks import register_get_auth_hook
import pytz

def arctic_auth_hook(mongo_host, app, database):
  return Credential(
    database="arctic",
    user="juan",
    password="ijosdeputa2",
  )

def view_arctic_db():
  register_get_auth_hook(arctic_auth_hook)
  store = Arctic('172.19.0.2:27017')

  store.initialize_library("crypto_ohlcv")

  library = store['crypto_ohlcv']

  print (library.list_symbols())

def drop_arctic_db(symbols = ['LTC', 'ETH', 'BTC','XRP', 'EOS']):
  register_get_auth_hook(arctic_auth_hook)
  store = Arctic('mongodb-server:27017')

  library = store['crypto_ohlcv']

  for symbol in symbols:
    library.delete(symbol)
  
#drop_arctic_db()
view_arctic_db()
