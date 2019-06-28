
import atexit
import pythoncom, time, os
from datetime import datetime as dt
import comtypes.client
comtypes.client.GetModule(r'./x86/SKCOM.dll')
import comtypes.gen.SKCOMLib as sk
import traceback

from DataUpdater2 import *
from TradeSignal import TradeSignal

import pandas as pd
import pymongo
import threading
import signal
signal.signal(signal.SIGINT, signal.SIG_DFL)


skC = comtypes.client.CreateObject(sk.SKCenterLib, interface = sk.ISKCenterLib)
skO = comtypes.client.CreateObject(sk.SKOrderLib, interface = sk.ISKOrderLib)
skQ = comtypes.client.CreateObject(sk.SKQuoteLib, interface = sk.ISKQuoteLib)
skR = comtypes.client.CreateObject(sk.SKReplyLib, interface = sk.ISKReplyLib)

# import win32com.client 
# from ctypes import WinDLL,byref
# from ctypes.wintypes import MSG
# SKCenterLib = win32com.client.Dispatch('{AC30BAB5-194A-4515-A8D3-6260749F8577}')
# SKOrderLib = win32com.client.Dispatch('{54FE0E28-89B6-43A7-9F07-BE988BB40299}')



# sTradeType //0:ROD  1:IOC  2:FOK
ROD = 0
IOC = 1
FOK = 2
# sBuySell   //0:買進 1:賣出
BUY = 0
SELL = 1
# sDayTrade  //當沖0:否 1:是，可當沖商品請參考交易所規定。
N_DAY_TRADE = 0
DAY_TRADE = 1
# sNewClose  //新平倉，0:新倉 1:平倉 2:自動{新期貨、選擇權使用}
NEW_POSI = 0
CLOSE_POSI = 1
AUTO_POSI = 2 
# sReserved  //盤別，0:盤中(T盤及T+1盤)；1:T盤預約{新期貨、停損單使用}
OPEN_IN = 0
OPEN_OUT = 1
# bstrTrigger //觸發價。{停損、移動停損、選擇權停損、MIT下單使用}
# bstrMovingPoint //移動點數。{移動停損下單使用}

B_STR = 'B'
S_STR = 'S'
N_STR = 'N'

VOLUME = 1
STOP_LOSS = 8
STOP_PROFIT = 21
MOVING_POINT = '10'

Mongo_ip = ''
Mongo_port = ''
Mongo_user = ''
Mongo_password = ''
Mongo_auth = ''
Mongo_uri = 'mongodb://' + Mongo_user + ':' + Mongo_password + '@' + Mongo_ip + ':' + Mongo_port + '/' + Mongo_auth




def Logs(msg):
	now = dt.now()
	strMsg = '[{}] {}'.format(now, msg)
	print(strMsg)

	with open('./TradingLogs.txt', 'a') as file:
		writer = file.write(strMsg + '\n')


class DataMongo(object):
	def __init__(self):
		try:
			self.client = pymongo.MongoClient(Mongo_uri)

		except pymongo.errors.ConnectionFailure as e:
			print('Could not connect to server:', e)

	def insert(self, db, coll, data):
		db = self.client[db][coll]
		db.insert_many(data)

	

class SKQuoteLibEvents:
	 
	def __init__(self, handler):
	
		self.__isReady = False


		self.handler = handler

		self.Lock = threading.Lock()

		self.HistortTicks = []
		self.Ticks = []
		# self.KLineData = []
		self.KLineData = {'Time':[], 'Open':[], 'High':[], 'Low':[], 'Close':[], 'Volume':[]}

	def OnConnection(self, nKind, nCode):
		if (nKind == 3001):
			strMsg = 'Connected!'
		elif (nKind == 3002):
			strMsg = 'DisConnected!'
		elif (nKind == 3003):
			strMsg = 'Stocks ready!'
			self.__isReady = True
		elif (nKind == 3021):
			strMsg = 'Connect Error!'
		Logs('Quote Server : {}'.format(strMsg))

	def OnNotifyQuote(self, sMarketNo, sStockidx):
		pStock = sk.SKSTOCK()
		skQ.SKQuoteLib_GetStockByIndex(sMarketNo, sStockidx, pStock)
		strMsg = '代碼:',pStock.bstrStockNo,'--名稱:',pStock.bstrStockName,'--開盤價:',pStock.nOpen/math.pow(10,pStock.sDecimal),'--最高:',pStock.nHigh/math.pow(10,pStock.sDecimal),'--最低:',pStock.nLow/math.pow(10,pStock.sDecimal),'--成交價:',pStock.nClose/math.pow(10,pStock.sDecimal),'--總量:',pStock.nTQty
		Logs(strMsg)
		

	def OnNotifyHistoryTicks(self, sMarketNo, sStockIdx, nPtr, lDate, lTimehms, lTimemillismicros, nBid, nAsk, nClose, nQty, nSimulate):
		if nSimulate == 0:
			strMsg = lDate, lTimehms, lTimemillismicros, nBid, nAsk, nClose, nQty
			self.handler.updateTick(strMsg)

		

	def OnNotifyTicks(self,sMarketNo, sStockIdx, nPtr, lDate, lTimehms, lTimemillismicros, nBid, nAsk, nClose, nQty, nSimulate):
		if nSimulate == 0:
			strMsg = lDate, lTimehms, lTimemillismicros, nBid, nAsk, nClose, nQty
			self.handler.updateTickForSignal(strMsg)
			
		

	# def OnNotifyBest5(self, sMarketNo, sStockidx, nBestBid1, nBestBidQty1, nBestBid2, nBestBidQty2, nBestBid3, nBestBidQty3, nBestBid4, nBestBidQty4, nBestBid5, nBestBidQty5, nExtendBid, nExtendBidQty, nBestAsk1, nBestAskQty1 , nBestAsk2, nBestAskQty2, nBestAsk3, nBestAskQty3, nBestAsk4, nBestAskQty4, nBestAsk5, nBestAskQty5, nExtendAsk, nExtendAskQty, nSimulate):
	# 	strMsg = nBestBid1, nBestAsk1
	# 	Logs(strMsg)

	def OnNotifyKLineData(self,bstrStockNo,bstrData):

		strMsg = bstrStockNo,bstrData
		# Logs(strMsg)

		self.AddKlineData(bstrData)


	def GetReady(self):
		return self.__isReady

	def GetTicks(self):
		strMsg = ''
		with self.Lock:
			if self.Ticks:
				strMsg = self.Ticks.pop(0)

		return strMsg

	def AddKlineData(self, bstrData):

		cutData = bstrData.split(',')

		self.KLineData['Time'].append(dt.strptime(cutData[0].replace('/', '-')+':00', '%Y-%m-%d %H:%M:%S'))
		self.KLineData['Open'].append(float(cutData[1].replace(' ', '')))
		self.KLineData['High'].append(float(cutData[2].replace(' ', '')))
		self.KLineData['Low'].append(float(cutData[3].replace(' ', '')))
		self.KLineData['Close'].append(float(cutData[4].replace(' ', '')))
		self.KLineData['Volume'].append(float(cutData[5].replace(' ', '')))

	def GetKLineData(self):
		df = pd.DataFrame(self.KLineData)
		df.Time = pd.to_datetime(df.Time)
		return df 

class SKOrderLibEvent:


	def __init__(self, handler):
		
		self.handler = handler

		self.account_list = {}

		self.bs_temp = [B_STR, S_STR]
		self.open_interest = {B_STR : 0, S_STR : 0}
		self.isInterRest = True

	def OnAccount(self, bstrLogInID, bstrAccountData):
		strValues = bstrAccountData.split(',')
		strAccount = strValues[1] + strValues[3]

	
		if strValues[0] == 'TS':
			self.account_list['stock'] = strAccount
			
		elif strValues[0] == 'TF':
			self.account_list['future'] = strAccount
			
		elif strValues[0] == 'OF':
			self.account_list['sea_future'] = strAccount
			
		elif strValues[0] == 'OS':
			self.account_list['foreign_stock'] = strAccount
	
	def OnAsyncOrder(self, nThreadID, nCode, bstrMessage):

		Logs('Async Order - threadID : {}, nCode : {}, message : {}'.format(nThreadID, nCode, bstrMessage))

	def OnOpenInterest(self, bstrData):
		
		if bstrData[0] != '#':
			cutData = bstrData.split(',')
			if len(cutData) > 2:
				
				mer = cutData[2]
				bs = cutData[3]
				vol = int(cutData[4])
				dayVol = int(cutData[5])

				print('test 1 : ', cutData)
				if mer[0] == self.handler.merchandise[0]:
					print('test 2 : ', cutData)
					if bs == B_STR:
						self.open_interest[B_STR] = int(vol)
						self.bs_temp.remove(B_STR)
					elif bs == S_STR:
						self.open_interest[S_STR] = int(vol)
						self.bs_temp.remove(S_STR)
			
		elif bstrData[0] == '#':

			if B_STR in self.bs_temp:
				self.open_interest[B_STR] = 0
			if S_STR in self.bs_temp:
				self.open_interest[S_STR] = 0

			self.bs_temp = [B_STR, S_STR] 

			Logs('Open Interest : {}'.format(self.open_interest))

	def GetOpenInterest(self):
		return self.open_interest

	def GetAccount(self):
		return self.account_list


class SKReplyLibEvent:

	def __init__(self, handler):
		self.handler = handler

	def OnNewData(self,strUserID,StrData):
		# print('on new data : {} / {}'.format(strUserID, StrData))

		cutData = StrData.split(',')
		if cutData[8][0] == self.handler.merchandise[0]:
			if cutData[2] == 'D':
				if cutData[6][1] == 'O':
					self.handler.initTradeStatus()
					Logs('Postion is Closed : {}'.format(StrData))

class Trader(object):

	def __init__(self, username, password, exchange, merchandise, isReal):

		self.isReal = isReal
		if not self.isReal:
			skC.SKCenterLib_ResetServer ('morder1.capital.com.tw')
		# else:
		# 	skC.SKCenterLib_ResetServer('Order2.capital.com.tw')

		self.username = username
		self.password = password
		self.exchange = exchange
		self.merchandise = merchandise


		self.SKOrderEvent = SKOrderLibEvent(self)
		self.SKOrderLibEventHandler = comtypes.client.GetEvents(skO, self.SKOrderEvent)

		self.SKQuoteEvent = SKQuoteLibEvents(self)
		self.SKQuoteLibEventHandler = comtypes.client.GetEvents(skQ, self.SKQuoteEvent)
		
		self.SKReplyEvent = SKReplyLibEvent(self)
		self.SKReplyLibEventHandler = comtypes.client.GetEvents(skR, self.SKReplyEvent)

		self.account_list = None


		self.updater = select_updater(self.exchange)

		self.isRun = True
		self.isTrade = False
		
		self.tradeThread = threading.Thread()

		self.position = N_STR
		self.signal = N_STR


		self.tradeSignal = TradeSignal()
		
		self.cur_time = None



	def __pumpwait(self):

		while self.isTrade:
			pythoncom.PumpWaitingMessages()

	def __pumpwaitForT(self, t=1):

		for i in range(t):
			time.sleep(1)
			pythoncom.PumpWaitingMessages()

	def record(self):
		if self.__login():

			res = skQ.SKQuoteLib_EnterMonitor()		
			strMsg = skC.SKCenterLib_GetReturnCodeMessage(res)
			Logs('Enter Monitor : {}'.format(strMsg))
			self.__pumpwaitForT(8)

			res = skQ.SKQuoteLib_RequestKLineAM(self.merchandise, sKLineType = 0, sOutType = 1, sTradeSession = 0)
			strMsg = skC.SKCenterLib_GetReturnCodeMessage(res)
			Logs('Request K Line : {}'.format(strMsg))

			df_klin = self.SKQuoteEvent.GetKLineData()
			list_kline = df_klin.T.to_dict().values()

			mongo = DataMongo()
			mongo.insert('TWS', 'TX00', list_kline)

		else:
			Logs('Close Recording Program')


	def FutureOrder(self, async, sMer, sBuySell, sTradeType, sDayTrade, sPrice, sVol, sNewClose, sReserved):

		# 建立下單用的參數(FUTUREORDER)物件(下單時要填商品代號,買賣別,委託價,數量等等的一個物件)
		oOrder = sk.FUTUREORDER()
		# 填入完整帳號
		oOrder.bstrFullAccount =  self.account_list['future']
		# 填入期權代號
		oOrder.bstrStockNo = sMer
		# 買賣別
		oOrder.sBuySell = sBuySell
		# ROD、IOC、FOK
		oOrder.sTradeType = sTradeType
		# 非當沖、當沖
		oOrder.sDayTrade = sDayTrade
		# 委託價
		oOrder.bstrPrice = sPrice
		# 委託數量
		oOrder.nQty = sVol
		# 新倉、平倉、自動
		oOrder.sNewClose = sNewClose
		# 盤中、T盤預約
		oOrder.sReserved = sReserved

		

		resMsg, res = skO.SendFutureOrder(self.username, async, oOrder)
		strMsg = skC.SKCenterLib_GetReturnCodeMessage(res)
		

		Logs('Order {} @ {}, Vol : {}, msg :{}'.format(sMer, sPrice, sVol, strMsg))
		
		if res == 0:
			return True, resMsg
		else:
			return False, resMsg

	def FutureOCOOrder(self, async, sMer, sBuySell, sBuySell2, sTradeType, sDayTrade, sPrice, sPrice2, sTrigger, sTrigger2, sVol, sNewClose, sReserved):

		# 建立下單用的參數(FUTUREORDER)物件(下單時要填商品代號,買賣別,委託價,數量等等的一個物件)
		oOrder = sk.FUTUREOCOORDER()
		# 填入完整帳號
		oOrder.bstrFullAccount =  self.account_list['future']
		# 填入期權代號
		oOrder.bstrStockNo = sMer
		# 買賣別
		oOrder.sBuySell = sBuySell
		oOrder.sBuySell2 = sBuySell2
		# ROD、IOC、FOK
		oOrder.sTradeType = sTradeType
		# 非當沖、當沖
		oOrder.sDayTrade = sDayTrade
		# 委託價
		oOrder.bstrPrice = sPrice
		oOrder.bstrPrice2 = sPrice2
		# 觸發價
		oOrder.bstrTrigger = sTrigger
		oOrder.bstrTrigger2 = sTrigger2
		# 委託數量
		oOrder.nQty = sVol
		# 新倉、平倉、自動
		oOrder.sNewClose = sNewClose
		# 盤中、T盤預約
		oOrder.sReserved = sReserved

		resMsg, res = skO.SendFutureOCOOrder(self.username, async, oOrder)
		strMsg = skC.SKCenterLib_GetReturnCodeMessage(res)
		
		Logs('OCO Order 1 {} @ {}, Vol : {}, OCO Order 2 {} @ {}, Vol : {}, msg : {}'.format(sMer, sTrigger, sVol, sMer, sTrigger2, sVol, strMsg))
		
		if res == 0:
			return True, resMsg
		else:
			return False, resMsg


	def FutureStopOrder(self, async, sMer, sBuySell, sTradeType, sDayTrade, sPrice, sTrigger, sVol, sNewClose, sReserved):

		# 建立下單用的參數(FUTUREORDER)物件(下單時要填商品代號,買賣別,委託價,數量等等的一個物件)
		oOrder = sk.FUTUREORDER()
		# 填入完整帳號
		oOrder.bstrFullAccount =  self.account_list['future']
		# 填入期權代號
		oOrder.bstrStockNo = sMer
		# 買賣別
		oOrder.sBuySell = sBuySell
		# ROD、IOC、FOK
		oOrder.sTradeType = sTradeType
		# 非當沖、當沖
		oOrder.sDayTrade = sDayTrade
		# 委託價
		oOrder.bstrPrice = sPrice
		# 觸發價
		oOrder.bstrTrigger = sTrigger
		# 委託數量
		oOrder.nQty = sVol
		# 新倉、平倉、自動
		oOrder.sNewClose = sNewClose
		# 盤中、T盤預約
		oOrder.sReserved = sReserved

		resMsg, res = skO.SendFutureStopLossOrder(self.username, async, oOrder)
		strMsg = skC.SKCenterLib_GetReturnCodeMessage(res)
		
		Logs('Stop Order {} @ {}, Vol : {}, msg : {}'.format(sMer, sPrice, sVol, strMsg))
		
		if res == 0:
			return True, resMsg
		else:
			return False, resMsg


	def FutureMovingStopOrder(self, async, sMer, sBuySell, sTradeType, sDayTrade, sTrigger, sMovingPoint, sVol, sNewClose, sReserved):

		# 建立下單用的參數(FUTUREORDER)物件(下單時要填商品代號,買賣別,委託價,數量等等的一個物件)
		oOrder = sk.FUTUREORDER()
		# 填入完整帳號
		oOrder.bstrFullAccount =  self.account_list['future']
		# 填入期權代號
		oOrder.bstrStockNo = sMer
		# 買賣別
		oOrder.sBuySell = sBuySell
		# ROD、IOC、FOK
		oOrder.sTradeType = sTradeType
		# 非當沖、當沖
		oOrder.sDayTrade = sDayTrade
		# 觸發價
		oOrder.bstrTrigger = sTrigger
		# 移動點數
		oOrder.bstrMovingPoint = sMovingPoint
		# 委託數量
		oOrder.nQty = sVol
		# 新倉、平倉、自動
		oOrder.sNewClose = sNewClose
		# 盤中、T盤預約
		oOrder.sReserved = sReserved

		resMsg, res = skO.SendMovingStopLossOrder(self.username, async, oOrder)
		strMsg = skC.SKCenterLib_GetReturnCodeMessage(res)
		

		Logs('Trailing Order {} @ {} by {}, Vol : {}'.format(sMer, sTrigger, sMovingPoint, sVol))
		Logs('Trailing Order : {}'.format(strMsg))
		
		if res == 0:
			return True, resMsg
		else:
			return False, resMsg
	
	def CancelOrderBySeqNo(self, async, seqNo):

		resMsg, res = skO.CancelOrderBySeqNo(self.username, async, self.account_list['future'], seqNo)

		if res == 0:
			return True, resMsg
		else:
			return False, resMsg

	def __closeAllPosition(self):
		self.GetOpenInterest()
		self.__pumpwaitForT(5)
		interest = self.SKOrderEvent.GetOpenInterest()
		l_posi = interest[B_STR]
		s_posi = interest[S_STR]

		if l_posi > 0:
			Logs('Close Long Postion Vol : {}'.format(l_posi))
			succ, orderID = self.FutureOrder(False, self.merchandise, SELL, IOC, N_DAY_TRADE, 'M', l_posi, CLOSE_POSI, OPEN_IN)
			if succ:
				Logs('Close Long Postion Successfully : {}'.format(orderID))
		if s_posi > 0:
			succ, orderID = self.FutureOrder(False, self.merchandise, BUY, IOC, N_DAY_TRADE, 'M', s_posi, CLOSE_POSI, OPEN_IN)
			Logs('Close Short Postion Vol : {}'.format(s_posi))
			if succ:
				Logs('Close Short Postion Successfully : {}'.format(orderID))

	def GetOpenInterest(self):

		res = skO.GetOpenInterest(self.username, self.account_list['future'])
		# strMsg = skC.SKCenterLib_GetReturnCodeMessage(res)
		# Logs('Get Interest : {}'.format(strMsg))

	def __login(self):

		res = skC.SKCenterLib_Login(self.username, self.password)
		strMsg = skC.SKCenterLib_GetReturnCodeMessage(res)
		Logs('Login : {}'.format(strMsg))

		if res == 0 or res == 2003:
			res = skR.SKReplyLib_ConnectByID(self.username)
			strMsg = skC.SKCenterLib_GetReturnCodeMessage(res)
			Logs('Reply : {}'.format(strMsg))

			return True
		else:
			return False

	

	def __prepareTrade(self):

		res = skO.SKOrderLib_Initialize()
		strMsg = skC.SKCenterLib_GetReturnCodeMessage(res)
		Logs('Order Init : {}'.format(strMsg))

		if res == 0:

			skO.GetUserAccount()
			self.__pumpwaitForT(1)
			self.account_list = self.SKOrderEvent.GetAccount()
			Logs(self.account_list)

			if self.isReal:
				res = skO.ReadCertByID(self.username)
				strMsg = skC.SKCenterLib_GetReturnCodeMessage(res)
				Logs('Read Cert : {}'.format(strMsg))

			if res == 0 or res == 2005:
				return True
			else:
				Logs('Read Cert Failed')
				return False

		else:
			Logs('Order Init Failed')
			return False

	def __prepareData(self):


		res = skR.SKReplyLib_ConnectByID(self.username)
		strMsg = skC.SKCenterLib_GetReturnCodeMessage(res)
		Logs('Connect By ID : {}'.format(strMsg))

		res = skQ.SKQuoteLib_EnterMonitor()		
		strMsg = skC.SKCenterLib_GetReturnCodeMessage(res)
		Logs('Enter Monitor : {}'.format(strMsg))

		while not self.SKQuoteEvent.GetReady():
			self.__pumpwaitForT(2)

		self.updater = select_updater(self.exchange)

		if res == 0:
			
			# df_min = pd.DataFrame({'Time' : [dt.strptime('2018-12-01 08:00:00', '%Y-%m-%d %H:%M:%S')],
			# 						'Open': [1.],
			# 						'High': [1.],
			# 						'Low': [1.],
			# 						'Close' : [1.],
			# 						'Volume' : [1.]}).set_index('Time')



			res = skQ.SKQuoteLib_RequestKLineAM(self.merchandise, sKLineType = 0, sOutType = 1, sTradeSession = 0)
			strMsg = skC.SKCenterLib_GetReturnCodeMessage(res)
			Logs('Request K Line : {}'.format(strMsg))
			df_min = self.SKQuoteEvent.GetKLineData().set_index('Time')

			self.updater.delete_period(1, 'min')
			self.updater.delete_period(3, 'min')
			# self.updater.delete_period(5, 'min')
			self.updater.delete_period(15, 'min')
			self.updater.delete_period(1, 'hour')
			self.updater.delete_period(1, 'day')

			self.updater.set_default_data(df_min)

			page = -1
			res = skQ.SKQuoteLib_RequestTicks(page, self.merchandise)
			strMsg = skC.SKCenterLib_GetReturnCodeMessage(res[1])
			Logs('Request Ticks : {}'.format(strMsg))
			
			# page = -1
			# res = skQ.SKQuoteLib_RequestLiveTick(page, self.merchandise)
			# strMsg = skC.SKCenterLib_GetReturnCodeMessage(res[1])
			# Logs('Request Ticks : {}'.format(strMsg))


			while self.updater.processor.tick['bid1'] is None and self.updater.processor.tick['ask1'] is None:
				self.__pumpwaitForT(1)


		else:
			Logs('Quote Failed')

	
	def initTradeStatus(self):

		self.position = N_STR
		
	
	def trading(self):
		
		Logs('Open Trading Program')
		threading.Thread(target = self.__check_stage).start()

		time.sleep(2)

		while self.isTrade:
			if self.__login():
				
				if self.__prepareTrade():
					
					self.__prepareData()
					
					self.tradeThread = threading.Thread(target = self.__startTrade3)
					self.tradeThread.start()
				
					self.__pumpwait()

					self.__stopTrade()
					
			else:
				self.isRun = False
				break
		self.isRun = False
			

		Logs('Close Trading Program')

	def updateTick(self, tick):
	
		self.updater.update(tick)
		
		

	def updateTickForSignal(self, tick):
		
		self.updater.update(tick)
		self.updateSignal()

	def updateSignal(self):

		if self.cur_time != self.updater.marketdata.min5['Time'][-1]:

			self.signal = self.tradeSignal.MA_Break(self.updater.marketdata.min5[:-1])
			Logs('{} - {}'.format(self.cur_time, self.signal))
			self.cur_time = self.updater.marketdata.min5['Time'][-1]

	

	####### Trade Strategy 1 #######
	## Limit Open
	## OCO Close
	################################
	def __startTrade1(self):

		Logs('Start Trading')

		cur_time = None

		self.signal = S_STR

		while self.isTrade:
		
			# if cur_time != self.cur_time:
			if True:
				if self.position == N_STR:

					if self.signal == B_STR:
						price = self.updater.processor.tick['ask1']
						succ, orderID = self.FutureOrder(False, self.merchandise, BUY, IOC, N_DAY_TRADE, str(price), VOLUME, NEW_POSI, OPEN_IN)
						
						if succ:
							Logs('Long successfully, ID : {}'.format(orderID))
							self.position = B_STR
							self.__pumpwaitForT(5)
							self.GetOpenInterest()
							self.__pumpwaitForT(5)

							interest = self.SKOrderEvent.GetOpenInterest()

							if interest[B_STR] > 0:
								self.position = B_STR	
								
								trigger_p = str(price + STOP_PROFIT)
								trigger_l = str(price - STOP_LOSS)

								Logs('Profit trigger : {}, Loss trigger : {}'.format(trigger_p, trigger_l))

								succ, res = self.FutureOCOOrder(False, self.merchandise, SELL, SELL, IOC, N_DAY_TRADE,
															'M', 'M', trigger_p, trigger_l, VOLUME, NEW_POSI, OPEN_IN)

								if succ:
									Logs('OCO Order Successfully - {}'.format(res))
								else:
									Logs('OCO Order Failed - {}'.format(res))
									self.FutureOrder(False, self.merchandise, SELL, IOC, N_DAY_TRADE, 'M', VOLUME, NEW_POSI, OPEN_IN)
									self.isTrade = False
									self.isRun = False


							else:
								self.position = N_STR
								Logs('Strike Failed')
					

					elif self.signal == S_STR:
						price = self.updater.processor.tick['bid1']
						succ, orderID = self.FutureOrder(False, self.merchandise, SELL, IOC, N_DAY_TRADE, str(price), VOLUME, NEW_POSI, OPEN_IN)
						
						if succ:
							Logs('Short successfully, ID : {}'.format(orderID))
							self.position = S_STR
							self.__pumpwaitForT(5)
							self.GetOpenInterest()
							self.__pumpwaitForT(5)

							interest = self.SKOrderEvent.GetOpenInterest()

							if interest[S_STR] > 0:
								self.position = S_STR	
								
								trigger_p = str(price - STOP_PROFIT)
								trigger_l = str(price + STOP_LOSS)

								Logs('Profit trigger : {}, Loss trigger : {}'.format(trigger_p, trigger_l))

								succ, res = self.FutureOCOOrder(False, self.merchandise, BUY, BUY, IOC, N_DAY_TRADE,
															'M', 'M', trigger_l, trigger_p, VOLUME, NEW_POSI, OPEN_IN)

								if succ:
									Logs('OCO Order Successfully - {}'.format(res))
								else:
									Logs('OCO Order Failed - {}'.format(res))
									self.FutureOrder(False, self.merchandise, BUY, IOC, N_DAY_TRADE, 'M', VOLUME, NEW_POSI, OPEN_IN)
									self.isTrade = False
									self.isRun = False

							else:
								self.position = N_STR
								# Logs('Strike Failed')

			
				# elif self.position == B_STR:

				# 	if self.signal == S_STR:



				# elif self.position == S_STR:

				# 	if self.signal == B_STR:


				cur_time = self.cur_time

			time.sleep(1)

	####### Trade Strategy 2 #######
	## Market Open
	## OCO Close
	################################
	def __startTrade2(self):

		Logs('Start Trading')

		cur_time = None

		while self.isTrade:
		
			if cur_time != self.cur_time:
		
				if self.position == N_STR:

					if self.signal == B_STR:
						price = self.updater.processor.tick['ask1']
						succ, orderID = self.FutureOrder(False, self.merchandise, BUY, IOC, N_DAY_TRADE, 'M', VOLUME, NEW_POSI, OPEN_IN)
						
						if succ:
							
							self.position = B_STR
						
							trigger_p = str(price + STOP_PROFIT)
							trigger_l = str(price - STOP_LOSS)

							Logs('Long successfully, ID : {}, Strike price : {}, Profit trigger : {}, Loss trigger : {}'.format(orderID, price, trigger_p, trigger_l))

							succ, res = self.FutureOCOOrder(False, self.merchandise, SELL, SELL, IOC, N_DAY_TRADE,
														'M', 'M', trigger_p, trigger_l, VOLUME, CLOSE_POSI, OPEN_IN)

							if succ:
								Logs('OCO Order Successfully - {}'.format(res))
							else:
								Logs('OCO Order Failed - {}'.format(res))
								self.FutureOrder(False, self.merchandise, SELL, IOC, N_DAY_TRADE, 'M', VOLUME, NEW_POSI, OPEN_IN)
								self.isTrade = False
								self.isRun = False



					elif self.signal == S_STR:
						price = self.updater.processor.tick['bid1']
						succ, orderID = self.FutureOrder(False, self.merchandise, SELL, IOC, N_DAY_TRADE, 'M', VOLUME, CLOSE_POSI, OPEN_IN)
						
						if succ:
							
							self.position = S_STR
						
							trigger_p = str(price - STOP_PROFIT)
							trigger_l = str(price + STOP_LOSS)

							Logs('Short successfully, ID : {}, Strike price : {}, Profit trigger : {}, Loss trigger : {}'.format(orderID, price, trigger_p, trigger_l))

							succ, res = self.FutureOCOOrder(False, self.merchandise, BUY, BUY, IOC, N_DAY_TRADE,
														'M', 'M', trigger_l, trigger_p, VOLUME, CLOSE_POSI, OPEN_IN)

							if succ:
								Logs('OCO Order Successfully - {}'.format(res))
							else:
								Logs('OCO Order Failed - {}'.format(res))
								self.FutureOrder(False, self.merchandise, BUY, IOC, N_DAY_TRADE, 'M', VOLUME, CLOSE_POSI, OPEN_IN)
								self.isTrade = False
								self.isRun = False

				cur_time = self.cur_time

			time.sleep(1)


	####### Trade Strategy 3 #######
	## Market Open
	## Monving Stop Close
	################################
	def __startTrade3(self):

		Logs('Start Trading')

		cur_time = None

		while self.isTrade:
		
			if cur_time != self.cur_time:
		
				if self.position == N_STR:

					if self.signal == B_STR:
						price = self.updater.processor.tick['ask1']
						succ, orderID = self.FutureOrder(False, self.merchandise, BUY, IOC, N_DAY_TRADE, 'M', VOLUME, NEW_POSI, OPEN_IN)
						
						if succ:
							self.position = B_STR
							Logs('Long successfully, ID : {}, Strike price : {}'.format(orderID, price))
							
							succ, res = self.FutureMovingStopOrder(False, self.merchandise, SELL, IOC, N_DAY_TRADE, str(price), MOVING_POINT, VOLUME, CLOSE_POSI, OPEN_IN)

							if succ:
								Logs('Trailing Order Successfully - {}'.format(res))
							else:
								Logs('Trailing Order Failed - {}'.format(res))
								self.FutureOrder(False, self.merchandise, SELL, IOC, N_DAY_TRADE, 'M', VOLUME, CLOSE_POSI, OPEN_IN)
								self.isTrade = False
								self.isRun = False



					elif self.signal == S_STR:
						price = self.updater.processor.tick['bid1']
						succ, orderID = self.FutureOrder(False, self.merchandise, SELL, IOC, N_DAY_TRADE, 'M', VOLUME, NEW_POSI, OPEN_IN)
						
						if succ:
							self.position = S_STR
							Logs('Short successfully, ID : {}, Strike price : {}'.format(orderID, price))
						
							succ, res = self.FutureMovingStopOrder(False, self.merchandise, BUY, IOC, N_DAY_TRADE, str(price), MOVING_POINT, VOLUME, CLOSE_POSI, OPEN_IN)

							if succ:
								Logs('Trailing Order Successfully - {}'.format(res))
							else:
								Logs('Trailing Order Failed - {}'.format(res))
								self.FutureOrder(False, self.merchandise, BUY, IOC, N_DAY_TRADE, 'M', VOLUME, CLOSE_POSI, OPEN_IN)
								self.isTrade = False
								self.isRun = False

				cur_time = self.cur_time

			time.sleep(1)

	def __stopTrade(self):

		while self.tradeThread.is_alive():
			pass
		self.__closeAllPosition()
		self.initTradeStatus()
		Logs('Stop Trading')

	def __check_stage(self):

		while self.isRun:
			
			now = dt.now()
			
			if now.weekday() == 6:
				self.isTrade = False

			elif now.weekday() == 5:
				date = now.strftime('%F')
				stage0_from = dt.strptime(date + ' 00:00:00', '%Y-%m-%d %H:%M:%S')
				stage0_to = dt.strptime(date + ' 4:55:00', '%Y-%m-%d %H:%M:%S')
				if stage0_from <= now < stage0_to:
					self.isTrade = True
				else:
					self.isTrade = False

			else:
				if now.weekday() == 0:
					date = now.strftime('%F')
					stage0_from = dt.strptime(date + ' 0:00:00', '%Y-%m-%d %H:%M:%S')
					stage0_to = dt.strptime(date + ' 8:30:00', '%Y-%m-%d %H:%M:%S')
					
					stage1_from = dt.strptime(date + ' 13:40:00', '%Y-%m-%d %H:%M:%S')
					stage1_to = dt.strptime(date + ' 14:45:00', '%Y-%m-%d %H:%M:%S')
					

					if stage0_from <= now < stage0_to:
						self.isTrade = False
					elif stage1_from <= now < stage1_to:
						self.isTrade = False
					else:
						self.isTrade = True


				else:
					date = now.strftime('%F')
					stage0_from = dt.strptime(date + ' 4:55:00', '%Y-%m-%d %H:%M:%S')
					stage0_to = dt.strptime(date + ' 8:30:00', '%Y-%m-%d %H:%M:%S')

					stage1_from = dt.strptime(date + ' 13:40:00', '%Y-%m-%d %H:%M:%S')
					stage1_to = dt.strptime(date + ' 14:45:00', '%Y-%m-%d %H:%M:%S')

					if stage0_from <= now < stage0_to:
						self.isTrade = False
					elif stage1_from <= now < stage1_to:
						self.isTrade = False
					else:
						self.isTrade = True

			time.sleep(10)


if __name__ == '__main__':
	
	try:

		ID = ''
		PWD = ''
		EXCH = ''
		MER = ''
		isReal = True

		# ID = ''
		# PWD = ''
		# EXCH = ''
		# MER = ''
		# isReal = False

		
		trader = Trader(ID, PWD, EXCH, MER, isReal)
		trader.trading()
		# trader.record()
		
	except:
		traceback.print_exc()


