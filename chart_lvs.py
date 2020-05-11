
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
import base64
from utils import ZmqRelay
from datetime import datetime 


PATH 			 = os.path.dirname(os.path.abspath(sys.modules['__main__'].__file__))
with open( PATH+'/config.yaml' ) as fp:
	config = yaml.load(fp, Loader=yaml.FullLoader)

logger = logging.getLogger(__name__)
coloredlogs.DEFAULT_FIELD_STYLES = config['LOGGING_FIELD_STYLES']
coloredlogs.DEFAULT_LEVEL_STYLES = config['LOGGING_LEVEL_STYLES']
coloredlogs.install( level=config['LOGGING_LEVEL'], logger=logger, fmt=config['LOGGING_FORMAT'] ) 


class ChartLVS():
	def __init__(self, args):

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
		unique_fparts = unique_fparts.sort_values('longs_usd_value', ascending=False )
		unique_fparts = unique_fparts[:10]

		pprint(unique_fparts)


		# logger.info('Querying funding_data')
		# query = list(self.db['funding_data'].find())
		# funding =  pd.DataFrame(query)

		# logger.info('Querying bases')
		# query = list(self.db['bases'].find())
		# bases =  pd.DataFrame(query)


		logger.info('Making chart')
		fig = plt.figure(facecolor='black', figsize=(18, 20), dpi=100, constrained_layout=False)
		plt.suptitle('Bitfinex Leverage Usage ~ {} ~ by whalepool.io'.format(datetime.utcnow().replace(microsecond=0, second=0)), fontsize=18, fontweight='bold')

		plot_left = 0.1
		plot_width = 0.8 
		bottom = 0.1 
		height = 0.8
		# LEFT, BOTTOM, WIDTH, HEIGHT
		rect0 = [0.125, 0.68, 0.805, 0.27]
		rect1 = [0.01, 0.01, 0.98, 0.5]

		####################################################
		# Rect 0 
		fparts_list = (list(unique_fparts.index.values))
		fpart_colors = plt.cm.Pastel1(np.linspace(0, 1, len(fparts_list)))
		bars_width = 0.24
		spare_width = (1 - bars_width*3)/2

		# long_bar_colors = plt.cm.GnBu(np.linspace(1, 1, len(elements_long)))
		long_y_offset = np.zeros(len(fparts_list))

		# 'shorts_usd_value','shorts_funded_usd']

		row_labels = [ 'Net long $','Longs P/L ▲▼', 'Net Shorts', 'Shorts P/L ▲▼', 'Sum Net Long-Short','USD Volume']
		green_colors = plt.cm.Greens(np.linspace(0.4, 0.86, 4))
		red_colors = plt.cm.Reds(np.linspace(0.4, 0.8, 4))
		purple_colors = plt.cm.Purples(np.linspace(0.4, 0.8, 4))
		oranges_colors = plt.cm.Oranges(np.linspace(0.4, 0.8, 4))
		row_colors = np.asarray([
			green_colors[0],
			green_colors[2],
			red_colors[0],
			red_colors[2],
			purple_colors[1],
			oranges_colors[1],
		])


		cell_text = [[ [] for i in range(len(fparts_list)) ] for q in range(len(row_labels))]
		colors = [[ [] for i in range(len(fparts_list)) ] for q in range(len(row_labels))]
		data = [ [ [] for i in range(len(fparts_list)) ] for q in range(len(row_labels)) ]

		for idx,fpart in enumerate(fparts_list):

			tdata = unique_fparts.loc[fpart]

			# Longs
			longs_usd_value = tdata['longs_usd_value']
			longs_usd_value_formatted = "${0:,.0f}".format(longs_usd_value)
			data[0][idx] = longs_usd_value
			cell_text[0][idx] = longs_usd_value_formatted

			long_delta = tdata['longs_usd_value'] - tdata['longs_funded_usd']
			long_delta_formatted = "${0:,.0f}".format(long_delta)
			data[1][idx] = long_delta ##############################################
			cell_text[1][idx] = long_delta_formatted

			# Shorts
			shorts_usd_value = tdata['shorts_usd_value']
			shorts_usd_value_formatted = "{0:,.0f}".format(shorts_usd_value)
			data[2][idx] = shorts_usd_value
			cell_text[2][idx] = shorts_usd_value_formatted

			short_delta = tdata['shorts_usd_value'] - tdata['shorts_funded_usd']
			short_delta_formatted = "${0:,.0f}".format(short_delta)
			data[3][idx] = short_delta ##############################################
			cell_text[3][idx] = short_delta_formatted

			# Delta
			delta = longs_usd_value - shorts_usd_value
			delta_formatted = "${0:,.0f}".format(delta)
			data[4][idx] = delta
			cell_text[4][idx] = delta_formatted

			# Volume
			volume_usd = tdata['volume_usd']
			volume_usd_formatted = "${0:,.0f}".format(volume_usd)
			data[5][idx] = volume_usd
			cell_text[5][idx] = volume_usd_formatted
			

			colors[0] = [ row_colors[0] for i in range(10) ]
			colors[1] = [ row_colors[1] for i in range(10) ]
			colors[2] = [ row_colors[2] for i in range(10) ]
			colors[3] = [ row_colors[3] for i in range(10) ]
			colors[4] = [ row_colors[4] for i in range(10) ]
			colors[5] = [ row_colors[5] for i in range(10) ]


		row_colors = np.asarray([
			green_colors[0],
			green_colors[2],
			red_colors[0],
			red_colors[2],
			purple_colors[1],
			oranges_colors[1],
		])


		ax1 = fig.add_axes(rect0, facecolor='#f6f6f6') 
		ax1.margins(x=0,y=0)
		ax1.margins(x=0,y=0.05)
		ax1.set_xticks([])
		ax1.set_xlim(-spare_width,len(fparts_list)-spare_width)
		ax1.set_ylabel("USD Value", fontsize=10)
		ax1.yaxis.set_major_formatter(matplotlib.ticker.StrMethodFormatter('{x:,.0f}'))
		ax1t = ax1.twinx()
		ax1t.margins(x=0,y=0.05)
		ax1t.set_ylabel("USD Volume", fontsize=10)
		ax1t.yaxis.set_major_formatter(matplotlib.ticker.StrMethodFormatter('{x:,.0f}'))
		ax1t.spines['right'].set_color(oranges_colors[3])
		ax1t.yaxis.label.set_color(oranges_colors[3])
		ax1t.tick_params(axis='y', colors=oranges_colors[3])


		pdata = {
			'longs'  : { 
				'dkeys': [0,1],
				'axis': ax1,
				'colors': [green_colors[0], green_colors[2]]
			},
			'shorts' : { 
				'dkeys': [2,3],
				'axis': ax1,
				'colors': [red_colors[0], red_colors[2]]
			},
			'delta'  : { 
				'dkeys': [4],
				'axis': ax1,
				'colors': [purple_colors[1]]
			},
			'volume' : { 
				'dkeys': [5],
				'axis': ax1t,
				'colors': [oranges_colors[1]]
			}
		}
		bars_pos = np.arange(len(fparts_list)) - bars_width
		for i,dkeys in pdata.items():
			bars_pos = bars_pos + bars_width
			long_y_offset = np.zeros(len(fparts_list))
			color = [0.05137255, 0.35098039, 0.70588235, 1.        ]

			if len(dkeys['dkeys']) >= 2:

				color = dkeys['colors'][0]
				barlist = dkeys['axis'].bar(bars_pos, data[dkeys['dkeys'][0]], bars_width, bottom=long_y_offset, color=color, alpha=1, zorder=0)

				long_y_offset = long_y_offset + data[dkeys['dkeys'][0]] - data[dkeys['dkeys'][1]]
				color = dkeys['colors'][1]
				barlist = dkeys['axis'].bar(bars_pos, data[dkeys['dkeys'][1]], bars_width, bottom=long_y_offset, color=color, alpha=1, zorder=1)

			else:
				long_y_offset = np.zeros(len(fparts_list))
				color = dkeys['colors'][0]
				barlist = dkeys['axis'].bar(bars_pos, data[dkeys['dkeys'][0]], bars_width, bottom=long_y_offset, color=color, alpha=1, zorder=0)



		the_table = ax1.table(cellText=cell_text,
		                      cellColours=colors,
		                      colLabels=fparts_list,
		                      colColours=fpart_colors,
		                      rowLabels=row_labels,
		                      rowColours=row_colors,
                        	cellLoc='center',
		                      loc='bottom')
		                      # bbox=[0.0,-0.2,1,0.2])
		the_table.auto_set_font_size(False)
		the_table.set_fontsize(12)
		the_table.scale(1,2.5)

		# cellDict = the_table.get_celld()
		# for x in range(1, len(row_labels)+1):
		# 	cellDict[(x,-1)]._loc = 'right'
		# 	cellDict[(x,-1)].set_color('red')



		def align_yaxis(ax1, ax2):
			"""Align zeros of the two axes, zooming them out by same ratio"""
			axes = (ax1, ax2)
			extrema = [ax.get_ylim() for ax in axes]
			tops = [extr[1] / (extr[1] - extr[0]) for extr in extrema]
			# Ensure that plots (intervals) are ordered bottom to top:
			if tops[0] > tops[1]:
			    axes, extrema, tops = [list(reversed(l)) for l in (axes, extrema, tops)]

			# How much would the plot overflow if we kept current zoom levels?
			tot_span = tops[1] + 1 - tops[0]

			b_new_t = extrema[0][0] + tot_span * (extrema[0][1] - extrema[0][0])
			t_new_b = extrema[1][1] - tot_span * (extrema[1][1] - extrema[1][0])
			axes[0].set_ylim(extrema[0][0], b_new_t)
			axes[1].set_ylim(t_new_b, extrema[1][1])

		align_yaxis(ax1, ax1t)


		####################################################
		# Rect 1 
		ax2 = fig.add_axes(rect1, facecolor='#f6f6f6') 
		ax2.set_xticks([])
		ax2.set_yticks([])
		ax2.margins(0.05)


		breakdowndf = unique_tickers[unique_tickers['fpart'].isin(fparts_list)]
		breakdowndf = breakdowndf.groupby("ticker").last()
		breakdowndf = breakdowndf.reset_index()
		breakdowndf = breakdowndf[ breakdowndf['longs_total_cnt'] > 0 ]

		# bdowndf = pd.DataFrame([]
		dfs = []
		for fpart in fparts_list:
			tmpdf = breakdowndf[ breakdowndf['fpart'] == fpart ]
			tmpdf = tmpdf.sort_values('longs_usd_value', ascending=False )
			dfs.append(tmpdf)
			
		bdowndf = pd.concat( dfs, axis=0 ) 
		bdowndf = bdowndf.reset_index()

		bcolumns = [
			'Ticker', 
			'Net Longs', 'Long margin usage', 'Longs P/L ▲▼',
			'Net Shorts', 'Short margin usage', 'Shorts P/L ▲▼',
			]
		rowlabels = list(breakdowndf.index.values)
		cpallett = { 
			'heading': '#f7e4ad',
			'row_green': '#b3ffb3',
			'row_group_green': '#e6ffe6',
			'row_red': '#ff8566',
			'row_group_red': '#ffe6e6',
			'row_color_blank1': '#f2f2f2',
			'row_color_blank2': '#cccccc',
		}

		cell_text = []
		cell_text.append(bcolumns)
		colors = []
		colors.append([ cpallett['heading'] for i in bcolumns ]) # 

		for row in range(len(bdowndf)):

			tdata = bdowndf.iloc[row]
			trow = []
			# Ticker 
			trow.append(tdata['ticker'])

			# Net Longs
			longs_total_cnt = "{0:,.0f}".format(tdata['longs_total_cnt'])
			longs_lpart_value = "{0:,.0f}".format(tdata['longs_lpart_value'])
			longs_usd_value = "{0:,.0f}".format(tdata['longs_usd_value'])
			trow.append( "{} ⇝ worth {} {}, (${})".format( longs_total_cnt, longs_lpart_value, tdata['lpart'], longs_usd_value ) )
			
			# Long margin usage
			longs_funded_usd = "{0:,.0f}".format(tdata['longs_funded_usd'])
			longs_funded_fpart = "{0:,.0f}".format(tdata['longs_funded_usd'] / tdata['fpart_usd_price'])
			trow.append( "${} ⇜ worth {} {}".format(longs_funded_usd, longs_funded_fpart, tdata['fpart']))
			
			# Longs P/L ▲▼
			long_delta = tdata['longs_usd_value'] - tdata['longs_funded_usd']
			long_delta_formatted = "{0:,.0f}".format(long_delta)
			if long_delta > 0:
				prefix = '++'
			else:
				prefix = '--'
			trow.append( "{}${}".format(prefix, long_delta_formatted) )
			
			# Net Shorts
			shorts_total_cnt = "{0:,.0f}".format(tdata['shorts_total_cnt'])
			shorts_lpart_value = "{0:,.0f}".format(tdata['shorts_lpart_value'])
			shorts_usd_value = "{0:,.0f}".format(tdata['shorts_usd_value'])
			trow.append( "{} ⇸ worth ${}".format(shorts_total_cnt, shorts_usd_value) )
			
			# Short margin usage
			shorts_funded = "{0:,.0f}".format(tdata['shorts_funded'])
			shorts_funded_usd = "{0:,.0f}".format(tdata['shorts_funded_usd'])
			trow.append( "{} ⇸ worth ${}".format(shorts_funded, shorts_funded_usd))

			# Shorts P/L ▲▼
			short_delta = tdata['shorts_usd_value'] - tdata['shorts_funded_usd']
			short_delta_formatted = "{0:,.0f}".format(short_delta)
			if short_delta > 0:
				prefix = '++'
			else:
				prefix = '--'
			trow.append( "{}${}".format(prefix, short_delta_formatted) )

			
			cell_text.append(trow)



			if long_delta > 0:
				row_color_longs = cpallett['row_group_green']
				row_color_longs = fpart_colors[fparts_list.index(tdata['fpart'])]
			else:
				row_color_longs = cpallett['row_group_red']
				row_color_longs = fpart_colors[fparts_list.index(tdata['fpart'])]

			if short_delta > 0:
				row_color_shorts = cpallett['row_group_green']
				row_color_shorts = fpart_colors[fparts_list.index(tdata['fpart'])]
			else:
				row_color_shorts = cpallett['row_group_red']
				row_color_shorts = fpart_colors[fparts_list.index(tdata['fpart'])]

			crow = []
			#Ticker 
			crow.append(fpart_colors[fparts_list.index(tdata['fpart'])])
			# Net Longs
			crow.append(row_color_longs)
			# Long margin usage
			crow.append(row_color_longs)
			# Longs P/L ▲▼
			crow.append(row_color_longs)
			# Net Shorts
			crow.append(row_color_shorts)
			# Short margin usage
			crow.append(row_color_shorts)
			# Shorts P/L ▲▼
			crow.append(row_color_shorts)

			colors.append(crow)

		# for cell in the_table._cells:
		# 	the_table._cells[cell].set_alpha(.5)

		# colors = plt.cm.GnBu(np.linspace(0.2, 0.8, len(rowlabels)))

		the_table2 = ax2.table(cellText=cell_text,
		                      # rowColours=colors,
		                      # colLabels=bcolumns,
		                      cellColours=colors,
		                      # loc='bottom',
		                      bbox=[0.0,0.0,1,1])
		# the_table2.auto_set_font_size(False)
		# the_table2.set_fontsize(10)
		the_table2.auto_set_column_width(col=list(range(len(bcolumns))))


		# Area chart histogram of margin long usage over time
		
		# Area chart histogram of margin short usage over time



		fname = PATH+'/out_lvs.png'
		plt.savefig(fname, pad_inches=1)
		logger.info('Saved {}'.format(fname))


		if args.pulse == True: 
			logger.info('Sending to pulse')
			pulse_sender = ZmqRelay('bfxpulse', singular=True)
			with open(fname, "rb") as image_file:
				img = base64.b64encode(image_file.read())
				img = img.decode("utf-8")
				img = "data:image/png;base64,"+img

				pdata =  {     
					'title': 'Bitfinex Margin Usage',    
					'content': "A full detailed breakdown of the highest volume tickers and their margin usage. \nAll source code available on github: https://github.com/Whalepool/WPBFXData",   
					'isPublic': 1, 
					'isPin': 0, 
					'attachments': [img]
					# 'attachments': []
				}

				pulse_sender.send_msg(pdata)

		if args.twitter == True: 
			logger.info('Sending to twitter')
			twitter_sender = ZmqRelay('twitter', singular=True)
			twdata = { 
				'msg': "Bitfinex \"Open Interest\" / Margin utilization. The highest volume tickers, \nAll source code available on github: https://github.com/Whalepool/WPBFXData\n\n$ETHUSD $BTCUSD",
				'picture': fname 
			}
			twitter_sender.send_msg( twdata )


		exit()


if __name__ == '__main__':

	parser = argparse.ArgumentParser()
	parser.add_argument('-t','--tickers', nargs='+', help='Ticker pairs to check data for', required=False)
	parser.add_argument('-twitter', help='post to twitter', action='store_true')
	parser.add_argument('-pulse', help='post to pulse', action='store_true')

	args = parser.parse_args()


	ChartLVS( args ) 