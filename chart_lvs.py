
from pprint import pprint
import coloredlogs, logging
import argparse
import sys
import os 
import yaml
from pymongo import MongoClient
import pandas as pd 
import numpy as np 
import matplotlib.pyplot as plt
import matplotlib 


PATH 			 = os.path.dirname(os.path.abspath(sys.modules['__main__'].__file__))
with open( PATH+'/config.yaml' ) as fp:
	config = yaml.load(fp, Loader=yaml.FullLoader)

logger = logging.getLogger(__name__)
coloredlogs.DEFAULT_FIELD_STYLES = config['LOGGING_FIELD_STYLES']
coloredlogs.DEFAULT_LEVEL_STYLES = config['LOGGING_LEVEL_STYLES']
coloredlogs.install( level=config['LOGGING_LEVEL'], logger=logger, fmt=config['LOGGING_FORMAT'] ) 


class ChartLVS():
	def __init__(self, argtickers):

		self.mclient 	= MongoClient(config['MONGO_CONNECTION_STRING'])
		self.db 			= self.mclient.bfxstats_new

		logger.info('Querying ticker_data')
		query = list(self.db['ticker_data'].find())


		ticker_data =  pd.DataFrame(query)
		ticker_data['timestamp'] = pd.to_datetime(ticker_data['timestamp'])
		# ticker_data = ticker_data.set_index('timestamp')	
		# ticker_data.index = ticker_data.index.tz_localize('UTC')	

		# tickers = ticker_data[ ticker_data['ticker'] == 'tBTCUSD' ]
		# tickers = tickers.resample('1H', label='right').mean()
		# data = data[start_date:end_date]

		# pprint('Making df of tickers')
		# do = ['BTC','ETH','EOS','XRP']
		# for d in do: 
		# 	unique_tickers = ticker_data.groupby("ticker").last()
		# 	unique_tickers = unique_tickers[['fpart','lpart','timestamp','longs_usd_value','longs_funded_usd','shorts_usd_value','shorts_funded_usd']]
		# 	unique_tickers = unique_tickers[ unique_tickers['fpart'] == d ]
			
		# 	pprint(unique_tickers)

		# 	eth_tickers = unique_tickers.groupby("fpart").sum()
		# 	eth_tickers['delta'] = eth_tickers['longs_usd_value']-eth_tickers['shorts_usd_value']
		# 	eth_tickers['longs_usd_value'] = eth_tickers.apply(lambda x: "{:,}".format(x['longs_usd_value']), axis=1)
		# 	eth_tickers['shorts_usd_value'] = eth_tickers.apply(lambda x: "{:,}".format(x['shorts_usd_value']), axis=1)
		# 	eth_tickers['delta'] = eth_tickers.apply(lambda x: "{:,}".format(x['delta']), axis=1)

		# 	pprint(eth_tickers)

		# 	end_c = '\033[0m'
		# 	green = '\u001b[38;5;154m'
		# 	print("{green}{ticker} L/S delta is {delta}{end_c}".format(green=green,ticker=d,delta=eth_tickers['delta'].values[0],end_c=end_c))

		
		unique_tickers = ticker_data.groupby("ticker").last()
		unique_tickers = unique_tickers.reset_index()
		# unique_tickers = unique_tickers[[
		# 	'ticker','fpart', 'lpart', 'timestamp',
		# 	'longs_total_cnt','longs_lpart_value','longs_usd_value',
		# 	'longs_funded','longs_funded_lpart_value','longs_funded_usd',
		# 	'shorts_total_cnt','shorts_lpart_value','shorts_usd_value',
		# 	'shorts_funded','shorts_funded_fpart_value','shorts_funded_usd',
		# ]]

		# unique_tickers = unique_tickers[unique_tickers['fpart'].isin(do)]
		# unique_tickers = unique_tickers.groupby("fpart").sum()
		# unique_tickers['longs_usd_value'] = unique_tickers.apply(lambda x: "{:,}".format(x['longs_usd_value']), axis=1)
		# unique_tickers['shorts_usd_value'] = unique_tickers.apply(lambda x: "{:,}".format(x['shorts_usd_value']), axis=1)
			
		pprint(unique_tickers)

		unique_fparts = unique_tickers.groupby("fpart").sum() 
		unique_fparts = unique_fparts.sort_values('longs_usd_value', ascending=False
			)
		unique_fparts = unique_fparts[:10]
		pprint(unique_fparts)


		# logger.info('Querying funding_data')
		# query = list(self.db['funding_data'].find())
		# funding =  pd.DataFrame(query)

		# logger.info('Querying bases')
		# query = list(self.db['bases'].find())
		# bases =  pd.DataFrame(query)


		logger.info('Making chart')
		fig = plt.figure(facecolor='black', figsize=(16, 16), dpi=100, constrained_layout=False)
		plt.suptitle('Bitfinex Margin Usage Analysis by whalepool.io', fontsize=18, fontweight='bold')

		plot_left = 0.1
		plot_width = 0.8 
		bottom = 0.1 
		height = 0.8
		# LEFT, BOTTOM, WIDTH, HEIGHT
		rect0 = [0.15, 0.65, 0.8, 0.3]
		rect1 = [0.15, 0.05, 0.8, 0.8]


		columns = (list(unique_fparts.index.values))
		index = np.arange(len(columns)) + 0.3
		y_offset = np.zeros(len(columns))
		bar_width = 0.4
		rows = ['longs_usd_value', 'longs_funded_usd' ]
		# 'shorts_usd_value','shorts_funded_usd']
		colors = plt.cm.GnBu(np.linspace(0.2, 0.8, len(rows)))

		data = []
		cell_text = []
		for columnname in rows:
			row = []
			ct_column = []
			for fpart in columns:
				# pprint('{} - {} - {}'.format(columnname,fpart, unique_fparts.loc[fpart][columnname]))
				row.append( unique_fparts.loc[fpart][columnname] )
				ct_column.append( "{0:,.0f}".format(unique_fparts.loc[fpart][columnname]) ) 

			data.append(row)
			cell_text.append(ct_column)


		ax1 = fig.add_axes(rect0, facecolor='#f6f6f6') 
		ax1.margins(x=0,y=0)
		ax1.margins(0.05)
		# ax2.set_ylim(0, tmpdf.loc[tmpdf['GLOBAL:USD'].idxmax()]['GLOBAL:USD']*1.06)

		n_rows = len(data)
		for row in range(n_rows):
			ax1.bar(index, data[row], bar_width, bottom=y_offset, color=colors[row])
			y_offset = y_offset + data[row]


		# Reverse colors and text labels to display the last value at the top.
		colors = colors[::-1]
		cell_text.reverse()


		# Add a table at the bottom of the axes
		rowlabels = ['Total Longs $ Value','Borrowed funds (in $)']
		the_table = ax1.table(cellText=cell_text,
		                      rowLabels=rowlabels,
		                      rowColours=colors,
		                      colLabels=columns,
		                      loc='bottom',
		                      bbox=[0.0,-0.2,1,0.2])
		the_table.set_fontsize(16)

		cellDict = the_table.get_celld()
		for x in range(1, len(rowlabels)+1):
			cellDict[(x,-1)]._loc = 'right'


		ax1.set_ylabel("USD Value", fontsize=10)
		ax1.yaxis.set_major_formatter(matplotlib.ticker.StrMethodFormatter('{x:,.0f}'))
		ax1.set_xticks([])

		ax2 = fig.add_axes(rect1, facecolor='#f6f6f6') 
		ax2.margins(0.05)
		ax2.xaxis.set_visible(False) 
		ax2.yaxis.set_visible(False)
		ax2.axis("off")

		breakdowndf = unique_tickers[unique_tickers['fpart'].isin(columns)]
		breakdowndf = breakdowndf.groupby("ticker").last()
		# breakdowndf = unique_tickers[[
		# 	'ticker','fpart', 'lpart',
		# 	'longs_total_cnt','longs_lpart_value','longs_usd_value',
		# 	'longs_funded','longs_funded_lpart_value','longs_funded_usd',
		# 	'shorts_total_cnt','shorts_lpart_value','shorts_usd_value',
		# 	'shorts_funded','shorts_funded_fpart_value','shorts_funded_usd',
		# ]]
		# pprint(breakdowndf)
		# pprint(breakdowndf.columns)
		# exit()

		bcolumns = [
			'Longs', 'Long margin utilization',
			'Shorts', 'Short margin utilziation',
			]
		rowlabels = list(breakdowndf.index.values)
		cell_text = []
		for row in range(len(breakdowndf)):
			tdata = breakdowndf.iloc[row]
			trow = []
			longs_total_cnt = "{0:,.0f}".format(tdata['longs_total_cnt'])
			longs_lpart_value = "{0:,.0f}".format(tdata['longs_lpart_value'])
			longs_usd_value = "{0:,.0f}".format(tdata['longs_usd_value'])
			trow.append( "{} longs worth {} {}, (${})".format( longs_total_cnt, longs_lpart_value, tdata['lpart'], longs_usd_value ) )
			
			longs_funded_usd = "{0:,.0f}".format(tdata['longs_funded_usd'])
			trow.append( "{} worth of margin used to support longs".format(longs_funded_usd))

			shorts_total_cnt = "{0:,.0f}".format(tdata['shorts_total_cnt'])
			shorts_lpart_value = "{0:,.0f}".format(tdata['shorts_lpart_value'])
			shorts_usd_value = "{0:,.0f}".format(tdata['shorts_usd_value'])
			trow.append( "{} shorts worth ${}".format(shorts_total_cnt, shorts_usd_value) )

			shorts_funded = "{0:,.0f}".format(tdata['shorts_funded'])
			shorts_funded_usd = "{0:,.0f}".format(tdata['shorts_funded_usd'])
			trow.append( "{} shorts are funded, worth ${}".format(shorts_funded, shorts_funded_usd))

			cell_text.append(trow)

		colors = plt.cm.GnBu(np.linspace(0.2, 0.8, len(rowlabels)))

		the_table2 = ax2.table(cellText=cell_text,
		                      rowLabels=rowlabels,
		                      rowColours=colors,
		                      colLabels=bcolumns,
		                      loc='bottom',
		                      bbox=[0.0,0,1,0.6])
		the_table2.set_fontsize(16)

		cellDict = the_table2.get_celld()
		for x in range(1, len(rowlabels)+1):
			cellDict[(x,-1)]._loc = 'right'



		fname = PATH+'/charts_lvs.png'
		plt.savefig(fname, pad_inches=1)
		logger.info('Saved {}'.format(fname))

		exit()


if __name__ == '__main__':

	parser = argparse.ArgumentParser()
	parser.add_argument('-t','--tickers', nargs='+', help='Ticker pairs to check data for', required=False)
	args = parser.parse_args()

	ChartLVS( args.tickers ) 