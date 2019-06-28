from TickProcessor import select_processor
from MarketData2 import MarketData2
import pandas as pd

class _UpdateCFH(object):

    def __init__(self):
        self.processor = select_processor('CFH')
        self.marketdata = MarketData2()

    def update(self, tick):

        tick = self.processor.process(tick)

        if len(tick) > 0:
            cur_time = tick['cur_time']
            bid = tick['bid1_price']
            ask = tick['ask1_price']
            
            if bid is None and ask is None:
                price = 0
            elif bid is None and ask is not None:
                price = ask
            elif bid is not None and ask is None:
                price = bid
            else:
                price = round(sum([bid, ask])/2, 5)
            
            if price != 0:
                tmp = pd.DataFrame({'Time':[cur_time], 'Price':[0]}).set_index('Time')

                for i in self.period:
                    period = i
                    interval = self.period_map[i]
                    past_interval = self.period[i]['cur_interval']
                    cur_interval = tmp.resample(interval).agg({'Price':'first'}).index[0]

                    if cur_interval != past_interval:
                        bid_qty = tick['bid1_qty']
                        ask_qty = tick['ask1_qty']
                        volume = sum(filter(None, [bid_qty, ask_qty]))/2
                    else:
                        volume = 0

                    self.period[i]['past_interval'] = past_interval
                    self.period[i]['cur_interval'] = cur_interval
                    
                    self.marketdata.update(period, price, volume, past_interval, cur_interval, keep = 15)


class _UpdateCTP(object):

    def __init__(self):
        self.processor = select_updater(exchange)
        self.marketdata = MarketData()

    def update(self, tick):
        tick = self.processor.process(tick, instrument)

        if len(tick) > 0:
            cur_time = tick['cur_time']
            price =  tick['last_price']
            volume = tick['last_qty']
            tmp = pd.DataFrame({'Time':[cur_time], 'Price':[0]}).set_index('Time')

            for i in self.period:
                period = i
                interval = self.period_map[i]
                past_interval = self.period[i]['cur_interval']
                cur_interval = tmp.resample(interval).agg({'Price':'first'}).index[0]

                self.period[i]['past_interval'] = past_interval
                self.period[i]['cur_interval'] = cur_interval

                self.marketdata.update(period, price, volume, past_interval, cur_interval)

class _UpdateSKTWS(object):

    def __init__(self):
        self.processor = select_processor('SKTWS')
        self.marketdata = MarketData2()

    def update(self, tick):

        tick = self.processor.process(tick)

       
        cur_time = tick['cur_time']
        bid = tick['bid1']
        ask = tick['ask1']
        price =  tick['price']
        
       
        tmp = pd.DataFrame({'Time':[cur_time], 'Price':[0]}).set_index('Time')

        for i in self.period:
            period = i
            interval = self.period_map[i]
            past_interval = self.period[i]['cur_interval']
            cur_interval = tmp.resample(interval, closed='right', label='right').agg({'Price':'first'}).index[0]

            if cur_interval != past_interval:
                qty = tick['qty']
                volume = qty
            else:
                volume = 0

            self.period[i]['past_interval'] = past_interval
            self.period[i]['cur_interval'] = cur_interval
            
            self.marketdata.update(period, price, volume, past_interval, cur_interval, keep = 1000)



def select_updater(exchange):
    exchange = exchange.upper()

    if exchange.upper() == 'CFH':
        obj = _UpdateCFH
    elif exchange.upper() == 'CTP':
        obj = _UpdateCTP
    elif exchange.upper() == 'SKTWS':
        obj = _UpdateSKTWS


    class DataUpdater(obj):
        def __init__(self):
            super(DataUpdater, self).__init__()
            self.__initialize_interval()

        def __initialize_interval(self):
            self.period = {'min1' : {'past_interval':None, 'cur_interval':None, 'interval':1, 'unit':'min'}, 
                           'min3' : {'past_interval':None, 'cur_interval':None, 'interval':3, 'unit':'min'}, 
                           'min5' : {'past_interval':None, 'cur_interval':None, 'interval':5, 'unit':'min'}, 
                           'min15' : {'past_interval':None, 'cur_interval':None, 'interval':15, 'unit':'min'}, 
                           'hour1' : {'past_interval':None, 'cur_interval':None, 'interval':1, 'unit':'H'}, 
                           'day1' :  {'past_interval':None, 'cur_interval':None, 'interval':1, 'unit':'D'}
                          }

            self.period_map = {'min1':'1min', 'min3':'3min', 'min5':'5min',
                               'min15':'15min', 'hour1': '1h', 'day1':'1d'}



        def set_new_period(self, interval, unit):
            unit = unit.lower()
            period = unit + str(interval)
            if period not in self.period:

                if unit == 'min':
                    m = str(interval) + 'min'
                elif unit == 'hour':
                    m = str(interval) + 'h'
                    unit = 'h'
                elif unit == 'day':
                    m = str(interval) + 'd'
                    unit = 'd'
                elif unit == 'sec':
                    m = str(interval) + 's'
                    unit = 's'

                self.period_map[period] = m

                df = self.marketdata.to_period(interval, unit, self.marketdata.min1)
                self.marketdata.set_new_data(period, df)

                self.period[period] =  {'interval':interval, 'unit':unit}
                self.period[period]['cur_interval'] = df.Time[-1]
                self.period[period]['past_interval'] = df.Time[-1]


                

        def delete_period(self, interval, unit):
            period = unit.lower() + str(interval)
            try:
                if hasattr(self.marketdata, period):
                    delattr(self.marketdata, period)
                self.period_map.pop(period)
                self.period.pop(period)


            except:
            	pass
        
        def set_default_data(self, df):
            df = df[~df.index.duplicated()]
            df = df.round(5)
            
            for i in self.period:
                period = i
                interval = self.period[i]['interval']
                unit = self.period[i]['unit']
                tmp_df = self.marketdata.to_period(interval, unit, df)
                self.marketdata.set_new_data(period, tmp_df)
                index = getattr(self.marketdata, period).Time[-1]
                self.period[i]['cur_interval'] = index
                self.period[i]['past_interval'] = index

    return DataUpdater()