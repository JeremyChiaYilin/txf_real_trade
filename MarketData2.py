from datetime import datetime as dt
from datetime import timedelta
import pandas as pd
import numpy as np

ohlc_dict = {                                                                                                             
    'Open':'first',                                                                                                    
    'High':'max',                                                                                                       
    'Low':'min',                                                                                                        
    'Close': 'last',                                                                                                    
    'Volume': 'sum'
}


class MarketData2(object):

    def __init__(self):
        self.__dtype=[('Time', 'datetime64[ns]'), 
                      ('Open', float),
                      ('High', float),
                      ('Low', float),
                      ('Close', float),
                      ('Volume', float)
                     ]
    
    def set_new_data(self, name, value):
        value.Volume = value.Volume.astype(float)
        value = value.to_records()
        setattr(self, name, value)
        
    def update(self, name, price, volume, past_interval, cur_interval, keep=1000):
        
        if hasattr(self, name):
            x = getattr(self, name)

            if past_interval == cur_interval:
                if price > x['High'][-1]:
                    x['High'][-1] = price
                if price < x['Low'][-1]:
                    x['Low'][-1] = price
                
                x['Close'][-1] = price
                x['Volume'][-1] += volume
            else:
                tick = np.rec.array([(cur_interval, price, price, 
                                      price, price, volume)], 
                                    dtype = self.__dtype)
                
                x = np.append(x, tick)

                if len(x) > keep:
                    x = np.delete(x, 0)
                                
            setattr(self, name, x)
        else:
            msg = 'could not find attribute[{}] in MarketData object'
            raise AttributeError(msg.format(name))
        
    def __convert(self, df, interval, unit):
        period = '{i}{u}'.format(i = interval, u = unit)
        df = df.resample(period, closed='right', label='right').agg(ohlc_dict)
        
        df = df.dropna(axis=0, how='any')
        df.reindex(pd.to_datetime(df.index.strftime('%F %T')))
        return df
        
    def to_period(self, interval = 1, unit = 'MIN', df = None, byname = '', inplace = False, new_name = ''):
        
        byname = str(byname)
        new_name = str(new_name)
        
        if byname != '' and hasattr(self, byname):
            df = getattr(self, byname).copy()
            
        elif isinstance(df, pd.DataFrame):
            df = df.copy()
            
        elif isinstance(df, (np.recarray, np.ndarray)):
            df = pd.DataFrame(df)
            df = df.set_index('Time')
            df.Volume = df.Volume.astype(float)
            
        else:
            print('No data to be convert!')
            return None
        
        df = self.__convert(df, interval, unit)

        if inplace:
            if new_name != '':
                self.set_new_data(new_name, df)
                
            if hasattr(self, byname):
                self.set_new_data(byname, df)
        else:
            return df