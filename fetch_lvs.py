
from pprint import pprint
import coloredlogs, logging
import argparse
import sys
import os 
import yaml
import json
import time
import requests
from math import log10, floor
from datetime import datetime 
from pymongo import MongoClient
from operator import itemgetter
from collections import OrderedDict
import copy

PATH 			 = os.path.dirname(os.path.abspath(sys.modules['__main__'].__file__))
with open( PATH+'/config.yaml' ) as fp:
	config = yaml.load(fp, Loader=yaml.FullLoader)

logger = logging.getLogger(__name__)
coloredlogs.DEFAULT_FIELD_STYLES = config['LOGGING_FIELD_STYLES']
coloredlogs.DEFAULT_LEVEL_STYLES = config['LOGGING_LEVEL_STYLES']
coloredlogs.install( level=config['LOGGING_LEVEL'], logger=logger, fmt=config['LOGGING_FORMAT'] ) 


class FetchLVS():
	def __init__(self, argtickers):


		self.mclient 	= MongoClient(config['MONGO_CONNECTION_STRING'])
		self.db 			= self.mclient.bfxstats_new
		self.current_minute = datetime.utcnow().replace(second=0,microsecond=0)
		self.api_request_cnt = []

		# query = "https://api.bitfinex.com/v1/symbols_details"
		# legacy = self.api_request(query)
		# self.tickers_legacy = {}
		# for t in legacy:
		# 	self.tickers_legacy[ t['pair'].upper() ] = OrderedDict({ 
		# 		'margin': 't'+t['margin'],
		# 		'price_precision': t['price_precision'],
		# 	})

		# https://docs.bitfinex.com/reference#rest-public-conf
		qs = [
			'pub:list:pair:margin', # Fetches an array of market information for each currency (WIP)
		]
		query = "https://api-pub.bitfinex.com/v2/conf/{}".format( ",".join(qs) )
		self.margin_tickers = OrderedDict()
		for m in self.api_request(query)[0]:
			self.margin_tickers['t'+m] = 1

		# Fetch all tickers/funding tickers 
		query = "https://api-pub.bitfinex.com/v2/tickers?symbols=ALL"
		if argtickers is not None:
			query = "https://api-pub.bitfinex.com/v2/tickers?symbols=t{}".format( ",t".join(argtickers) )
		all_ = self.api_request(query)

		self.tickers = OrderedDict()
		self.funding_data = OrderedDict()

		# Split them up  
		for el in all_:
			# Ticker
			if el[0][0] == 't':
				if el[0][-2:] == 'F0': # A future.. 
					continue 

				self.tickers[el[0]] = OrderedDict({ 
					'timestamp': self.current_minute,
					'ticker': el[0],
					'fpart': '',
					'lpart': '',
					'fpart_usd_price': 0,
					'lpart_usd_price': 0,
					'last_price': el[7],
					'last_price_usd': 0,
					'volume': el[8],
					'volume_usd': 0,
				})
			# Funding 
			if el[0][0] == 'f':
				self.funding_data[el[0]] = OrderedDict({
					'timestamp': self.current_minute,
					'ticker': el[0],
					'frr': el[1],
					'last_price': el[10],
					'volume': el[11],
					'frr_available': el[16]
				})

		# Extract the bases 
		self.bases = OrderedDict() 

		def add_to_bases(base):

			fiats  = { 
				'USD': ['$', ''], 
				'EUR': ['€', ''], 
				'JPY': ['¥', ''] , 
				'GBP': ['£', ''] , 
				'UST': ['t$', ' USDT'],
				'USTF0': ['f$', ' USDT'],
				'CNHT': ['t元', ' CNHT'],
			}

			if base not in self.bases:
				to_usd = 1
				pre = '' 
				post = ' '+base 

				for i,t in self.tickers.items():
					if t['ticker'] == 't'+base+'USD':
						to_usd = t['last_price']
					elif t['ticker'] == 't'+base+':USD':
						to_usd = t['last_price']

				if base in fiats:
					pre  = fiats[base][0]
					post = fiats[base][1]

				if base == 'USD':
					to_usd == 1
				elif to_usd == 1:
					# IF we can't get the BASE:USD exchange rate from self.tickers
					# IF the BASE is not USD 
					# Then we have to get the exchange rate from the fx api 
					to_usd = self.get_fx_rate( base, 'USD' )

				self.bases[base] = OrderedDict({ 
					'timestamp': self.current_minute,
					'fx': base,
					'to_usd': to_usd,
					'pre': pre, 
					'post': post 
				})

		for t,el in self.tickers.items():
			# https://github.com/bitfinexcom/lib-js-util-symbol/blob/master/index.js#L11

			if len(t) > 7:
				prim = t.split(':')[0][1:]
				base = t.split(':')[1]
			else:
				prim = t[1:-3]
				base = t[-3:]

			self.tickers[t]['fpart'] = prim
			self.tickers[t]['lpart'] = base 

			if el['ticker'] in self.margin_tickers:
				self.tickers[t]['margin'] = True
				add_to_bases(prim)
				add_to_bases(base)
				self.tickers[t]['last_price_usd'] = el['last_price'] * self.bases[base]['to_usd']
				self.tickers[t]['volume_usd'] = el['volume'] * self.tickers[t]['last_price_usd']
			else:
				self.tickers[t]['margin'] = False


		if argtickers is not None:
			self.top_tickers = []
			for ticker in argtickers:
				self.top_tickers.append('t'+ticker)


		# Go through tickers, create normalised USD price and volume
		self.tickers = OrderedDict(reversed(sorted(self.tickers.items(), key=lambda item: item[1]['volume_usd'])))

		# Get the current Top tickers
		self.top_tickers = list(self.tickers)[:config['MAX_TOP_TICKERS']]

		# Get the saved top tickers
		with open( PATH+'/config.lvstickers.yaml', 'r' ) as fp:
			saved_top_tickers = yaml.load(fp, Loader=yaml.BaseLoader)
			if saved_top_tickers == None:
				saved_top_tickers = {} 

		# Make sure our current top tickers list INCLUDES any saved top tickers 
		for ticker in saved_top_tickers:
			if ticker not in self.top_tickers:
				logger.debug('Adding {} to top_tickers from the saved_top_tickers list'.format(ticker))
				self.top_tickers.append(ticker)

		# Check our updated top ticker list are all still present on bfx (not delisted etc)
		# Only if no arg tickers are provided.. 
		# Otherwise argtickers will fucked up our saved top ticker list
		if argtickers is None:
			for idx,ticker in enumerate(self.top_tickers):
				if ticker not in self.tickers:
					logger.debug('Removing {} from saved_top_tickers'.format(ticker))
					del self.top_tickers[idx]

		# Save our current top tickers state
		with open( PATH+'/config.lvstickers.yaml', 'w' ) as fp:
			yaml.dump(self.top_tickers, fp, default_flow_style=False)

		# Cut the top tickers down to only do the number set by config
		self.top_tickers = self.top_tickers[:config['MAX_TOP_TICKERS']]

		logger.debug('Tickers: {}'.format(self.tickers))
		logger.debug('Funding Data: {}'.format(self.funding_data))
		logger.debug('Top Tickers: {}'.format(self.top_tickers))
		logger.debug('Bases: {}'.format(self.bases))


		# If we have argument supplied tickers to do 
		# Fuck the top tickers to get data for
		# Just force the supplied tickers to be top tickers
		# and get the data for them 
		if argtickers is not None:
			self.top_tickers = []
			for ticker in argtickers:
				self.top_tickers.append('t'+ticker)


		# Strip excess tickers
		do = []
		fund = []
		for ticker, el in self.tickers.items():
			if ticker not in self.top_tickers:
				do.append(ticker)
			else:
				fund.append('f'+el['fpart'])
				fund.append('f'+el['lpart'])


		end_c = '\033[0m'
		purple = '\u001b[38;5;141m'	
		blue = '\u001b[38;5;123m'
		green = '\u001b[38;5;40m'	

		# Get the LVS data for the top tickers
		for ticker, o in self.tickers.items():

			prefill = [
				'fpart_usd_price', 'lpart_usd_price',
				'longs_total_cnt','longs_lpart_value','longs_usd_value',
				'longs_funded', 'longs_funded_lpart_value', 'longs_funded_usd', 
				'shorts_total_cnt', 'shorts_lpart_value', 'shorts_usd_value',
				'shorts_funded', 'shorts_funded_fpart_value', 'shorts_funded_usd'
			]
			o = { **o, **{v:0 for k, v in enumerate(prefill) } }

			if o['margin'] == False:
				logger.info('IGNORING: {color}{ticker} has no margin available{end_c}'.format(color=purple, ticker=ticker, end_c=end_c))
				self.tickers[ticker] = o
				continue
			if o['ticker'] not in self.top_tickers:
				logger.info('IGNORING: {color}{ticker} has margin, BUT, is not a top ticker{end_c}'.format(color=blue, ticker=ticker, end_c=end_c))
				self.tickers[ticker] = o
				continue 

			# Get USD price for fpart (eg: ETH in the ETHBTC) 
			o['fpart_usd_price'] = self.bases[ o['fpart'] ]['to_usd']
			o['lpart_usd_price'] = self.bases[ o['lpart'] ]['to_usd']
			
			logger.info('{color}{ticker}  IS a top ticker so collecting LVS Data for it.{end_c}'.format(color=green, ticker=ticker, end_c=end_c))
			#############################
			# Total longs
			query = "https://api-pub.bitfinex.com/v2/stats1/pos.size:1m:{}:long/last".format(o['ticker'])
			o['longs_total_cnt']       = round( self.api_request(query)[1] )
			o['longs_lpart_value']  = round( o['longs_total_cnt'] * o['last_price'] )
			o['longs_usd_value']   = round( o['longs_total_cnt'] * o['last_price_usd'] )

			# Long funding
			query = "https://api-pub.bitfinex.com/v2/stats1/credits.size.sym:1m:f{}:{}/last".format( o['lpart'],o['ticker'])
			o['longs_funded']   = round( self.api_request(query)[1] )
			o['longs_funded_fpart_value']  = round( o['longs_funded'] / o['last_price'] )
			o['longs_funded_usd']  = round( o['longs_funded'] * o['lpart_usd_price'] )


			#############################
			# Total shorts
			query = "https://api-pub.bitfinex.com/v2/stats1/pos.size:1m:{}:short/last".format(o['ticker'])
			o['shorts_total_cnt']      = round( self.api_request(query)[1] )
			o['shorts_lpart_value'] = round( o['shorts_total_cnt'] * o['last_price'] ) 
			o['shorts_usd_value']  = round( o['shorts_total_cnt'] * o['last_price_usd'] )

			# Short funding  
			query = "https://api-pub.bitfinex.com/v2/stats1/credits.size.sym:1m:f{}:{}/last".format(o['fpart'],o['ticker'])
			o['shorts_funded']     = round( self.api_request(query)[1] )
			o['shorts_funded_fpart_value']  = round( o['shorts_funded'] * o['last_price'] )
			o['shorts_funded_usd'] = round( o['shorts_funded'] * o['fpart_usd_price'] )

			self.tickers[ticker] = o

		# Save Tickers
		logger.info('Inserting {} tickers to mongo'.format(len(self.tickers)))
		self.db['ticker_data'].insert_many( 
				[ dict(v) for k,v in self.tickers.items() if v['margin'] == True ], 
				ordered=True 
			)

		# Save Funding Data
		logger.info('Inserting {} funding data pairs to mongo'.format(len(self.funding_data)))
		self.db['funding_data'].insert_many( 
			[ dict(v) for k,v in self.funding_data.items() ], 
			ordered=True 
		)

		# Save Bases
		logger.info('Inserting {} bases to mongo'.format(len(self.bases)))
		self.db['bases'].insert_many( 
			[ dict(v) for k,v in self.bases.items() ],
			ordered=True 
		)


		# pprint(self.tickers)
		# pprint(self.tickers)
		# pprint(self.funding_data, depth=3)
		# pprint(self.top_tickers)
		# pprint(self.bases, depth=3)


		logger.info('Total: {} api request'.format(len(self.api_request_cnt)))

		exit()





	def get_fx_rate(self, curr1, curr2):

		url = 'https://api.bitfinex.com/v2/calc/fx'
		pairs = {"ccy1": curr1, "ccy2": curr2}

		logger.info( 'BFX API request #{}: {}, {}'.format( len(self.api_request_cnt), url, pairs) ) 
		self.api_request_cnt.append( "{} - {}".format(url, pairs ) )

		r = requests.post(url, json=pairs)
		if r.status_code != 200:
			logger.critical('Error in BFX FX rates request/reply: {}'.format(r.json()))
			exit()

		return float(r.json()[0]) 


	def api_request(self, url):
		
		logger.info( 'BFX API request #{}: {}'.format( len(self.api_request_cnt), url) ) 
		self.api_request_cnt.append( "{}".format(url ) )

		slow_api_time = 5 
		response = requests.get(url).text
		data     = json.loads(response)

		# Check we actually got the data back 
		# Not just an api error 
		completed = 0 
		while completed == 0:

			if isinstance(data, list):

				if str(data[0]) == 'error': 

					logger.error('BFX API Error: {}, sleeping {} to calm down..'.format(data, slow_api_time))
					time.sleep(slow_api_time)
					
					# Re-request the data
					logger.info( 'RE Request BFX API request #{}: {}'.format( len(self.api_request_cnt), url) ) 
					self.api_request_cnt.append( "{}".format(url ) )
					response = requests.get(url).text
					data = json.loads(response)
					logger.debug('Returned: {}'.format(data))

				else:
					# The response json does not contain error
					# Therefore we have the response we wanted
					# So api request actuall completed successfully
					completed = 1
					logger.debug('API request completed')
					logger.debug(data)

			elif isinstance(data, dict):

				if 'error' in data:

					logger.error('BFX API Error: {}, sleeping {} to calm down..'.format(data, slow_api_time))
					time.sleep(slow_api_time)
					
					# Re-request the data
					logger.info( 'RE Request BFX API request #{}: {}'.format( len(self.api_request_cnt), url) ) 
					self.api_request_cnt.append( "{}".format(url ) )
					response = requests.get(url).text
					data = json.loads(response)
					logger.debug('Returned: {}'.format(data))

			else:
				# WTF has the api returned then ? 
				logger.critical('WTF has the api returned ?')
				logger.critical(data)
				exit()	

		return data

	def round_sig(self, x, sig=5):
		return round(x, sig-int(floor(log10(abs(x))))-1)


if __name__ == '__main__':

	parser = argparse.ArgumentParser()
	parser.add_argument('-t','--tickers', nargs='+', help='Ticker pairs to check data for', required=False)
	args = parser.parse_args()

	FetchLVS( args.tickers ) 