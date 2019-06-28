import talib
import numpy as np

class TradeSignal(object):
    def __init__(self):
        pass

    def KD_Break(self, data, fastk_period = 9, slowk_period = 3, slowd_period = 3, fastd_period = 9):

        data_ = data.copy()

        high = data_['High']
        low = data_['Low']
        close = data_['Close']
        k, d = talib.STOCHF(high=high, low=low, close=close, fastk_period=fastk_period, fastd_period=fastd_period, fastd_matype=0)
        real = talib.ADX(high=high, low=low, close=close, timeperiod=10)
        
        fast_1 = k[-1]
        fast_2 = k[-2]
        slow_1 = d[-1]
        slow_2 = d[-2]

        cond1 = fast_2 < slow_2 and fast_1 > slow_1 and fast_1 < 30 and 20 <= real[-1] <= 50
        cond2 = fast_2 > slow_2 and fast_1 < slow_1 and fast_1 > 70 and 20 <= real[-1] <= 50
        
        
        if cond1:
            signal = 'B'
        elif cond2:
            signal = 'S'
        else:
            signal = 'N'

        return signal

    def MA_Break(self, data):

        data_ = data.copy()

        close = data_['Close']
        ma5 = np.mean(close[-5:])
        ma5_ = np.mean(close[-6:-1])
        ma10 = np.mean(close[-10:])
        ma10_ = np.mean(close[-11:-1])
        ma20 = np.mean(close[-20:])
        ma20_ = np.mean(close[-21:-1])

        print('present :', ma5_, ma10_, ma20_)
        print('current :', ma5, ma10, ma20)

        cond1 = ma5 > ma10 and ma5 > ma20 and ma5_ < ma20_
        cond2 = ma5 < ma10 and ma5 < ma20 and ma5_ > ma20_

        speed = abs(close[-1] - close[-8])
        fluc = 0
        for j in range(8):
            fluc += abs(close[-1-j] - close[-1-j-1])

        ratio = speed/fluc
        print('ratio : ', ratio)
        if cond1 and ratio >= 0.6:
            signal = 'B'
        elif cond2 and ratio >= 0.6:
            signal = 'S'
        else:
            signal = 'N'

        return signal


    def BB_Reverse(self, data, period = 22, nstd = 2):

        pth = 5

        data_ = data.copy()

        close = data_['Close'][-1 * period:]

       
        upperband, middleband, lowerband = talib.BBANDS(close, timeperiod = period , nbdevup = nstd, nbdevdn = nstd, matype = talib.MA_Type.SMA)

        upper = upperband[-1]
        lower = lowerband[-1]
        o = data_['Open'][-1]
        h = data_['High'][-1]
        l = data_['Low'][-1]
        c = data_['Close'][-1]
        diff_ = upper - lower

        signal = 'N'

        if 60 > diff_ and diff_ > 25:

            if c - o > pth or c - l > pth:
                if l <= lower:
                    signal = 'B'
               
            elif o - c > pth or h - c > pth:
                if h >= upper:
                    signal = 'S'
               
        return signal

    def MA_Trend_Following(self, data, period = 22):


        data_ = data.copy()
        close = data_['Close']
        open_ = data_['Open']
        ma = np.mean(close[-1*(period+1):-1])
        o_c = open_[-1]
        o_p = open_[-2]
        
        if o_c >= ma and o_p < ma:
            signal = 'B'
        elif o_c <= ma and o_p > ma:
            signal = 'S'
        else:
            signal = 'N'

        return signal
