
# -----------------
# import modules
# -----------------
import requests
import pandas as pd
import json
import datetime as dt
import os
import time

from pycoingecko import CoinGeckoAPI

from telethon.sync import TelegramClient
from telethon.tl.functions.messages import (GetHistoryRequest)
from telethon.tl.types import (PeerChannel)
from telethon.sync import TelegramClient

import config

from sklearn import datasets, linear_model
from sklearn.metrics import mean_squared_error, r2_score

# connect telegram
def connect_tg():

    client = TelegramClient(config.phone, config.api_id, config.api_hash)

    return client


def send_message(value):

    channel_api = 'bot'+ config.api_messages
    chat_id = config.chat_id_messages
    url = 'https://api.telegram.org/'+channel_api+'/sendMessage?chat_id=-'+chat_id+'&text="{}"'.format(value)
    requests.get(url)


# config
cg = CoinGeckoAPI()
url = 'https://api.coingecko.com/api/v3/search/trending'

# init data
def init_collect_data():
    col_names = ['name','coin_id','symbol','market_cap_rank']
    data  = pd.DataFrame(columns = col_names)
    return data

# store data
def store_data(data):
    data.to_csv(index=False)


def get_trending(data):
    url = 'https://api.coingecko.com/api/v3/search/trending'
    r = requests.get(url)
    data = json.loads(r.text)

    col_names = ['name','coin_id','symbol','market_cap_rank']
    df_temp  = pd.DataFrame(columns = col_names)
    df_trending  = pd.DataFrame(columns = col_names)

    for s in data['coins']:
        df_temp.loc[0,'name'] = s['item']['id']
        df_temp.loc[0,'coin_id'] = s['item']['coin_id']
        df_temp.loc[0,'symbol'] = s['item']['symbol']
        df_temp.loc[0,'market_cap_rank'] = s['item']['market_cap_rank']
        df_trending = df_trending.append(df_temp)

    df_trending.reset_index(drop=True, inplace=True)
    df_trending['rank'] = df_trending.index + 1
    df_trending['Date'] = pd.to_datetime("now")

    return df_trending


def time_series_to_ml(data,rolling_window):
    for i in range(1,rolling_window):
        column_name = 't-'+str(i)
        data[column_name] = data['rank'].shift(i)
    return data


def coin_predict(data,rolling_window):

    data = df_coin[['rank']]

    data = time_series_to_ml(data,rolling_window)

    data.dropna(axis=0, inplace=True)

    X_train = data.iloc[:,1:]
    y_train = data[['rank']]
    X_pred  = data.iloc[-1:,0:-1]

    regr = linear_model.LinearRegression()
    regr.fit(X_train, y_train)
    y_pred = regr.predict(X_pred)

    return y_pred



def main():

    client = connect_tg()
    client.connect()

    send_message('Connection ok: \n Tracking trending coins begins')

    #while True:
    count = 0
    while count < 6:

        count+=1
        data = init_collect_data()

        df_trending = get_trending(data)


        if 'df_top' in locals():
            df_trending['Iter'] = df_top.Iter.max() + 1
            df_top = df_top.append(df_trending)
        else:
            df_top = df_trending
            df_top['Iter'] = 1


        # df_top['Count'] = df_top.groupby(["Iter"]).coin_id.transform('count')

        df_top['Count'] = df_top.groupby(["coin_id"]).name.transform('count')


        time.sleep(100)

        df_top['Forecast'] = 0
        coin_list = df_top[df_top['Count']>4].coin_id.unique().tolist()

        rolling_window = 4

        for coin in coin_list:

            #coin = coin_list[0]
            df_coin = df_top[df_top['coin_id']==coin]
            df_coin.reset_index(drop=True, inplace=True)
            df_predict = df_coin[['rank']]

            y_pred = coin_predict(df_predict,rolling_window)

            if(float(y_pred)>=float(y_train[-1:].values)):  # note this needs to be changed
                df_top.loc[df_top.coin_id==coin,'Forecast'] = 1
                df_top.loc[df_top.coin_id==coin,'rank_fore'] = y_pred


        coins_trending_up = df_top[df_top['Forecast']==1].name.unique().tolist()

        if len(coins_trending_up)>0:
            text = ''
            coin_count = 0
            for coin in coins_trending_up:
                name = coin
                coin_count+=1
                market_cap_rank = df_top[(df_top.name==name) & (df_top.Iter==df_top['Iter'].max())].market_cap_rank.unique()
                rank = df_top[(df_top.name==name) & (df_top.Iter==df_top['Iter'].max())]['rank'].unique()
                rank_fore = df_top[df_top.name==name].rank_fore.unique()
                text+= '\n'+str(coin_count)+': \n Coin: ' + name + ' market_cap_rank: ' + str(market_cap_rank) + '\n Rank: ' + str(rank) + ' \n Rank fore: ' + str(rank_fore)

            send_text = 'Coins trending up are: \n' + text
            send_message(text)


        df_top['is_new'] = 0
        df_top.loc[(df_top['Count']==1) & (df_top['Iter']==df_top['Iter'].max()),'is_new'] = 1
        coins_new = df_top[df_top['is_new']==1].coin_id.unique().tolist()


        if len(coins_new)>0:
            text = ''
            coin_count = 0
            for coin in coins_new:
                name = coin
                coin_count+=1
                market_cap_rank = df_top[(df_top.name==name) & (df_top.Iter==df_top['Iter'].max())].market_cap_rank.unique()
                rank = df_top[(df_top.name==name) & (df_top.Iter==df_top['Iter'].max())]['rank'].unique()
                rank_fore = df_top[df_top.name==name].rank_fore.unique()
                text+= '\n'+str(coin_count)+': \n Coin: ' + name + ' market_cap_rank: ' + str(market_cap_rank) + '\n Rank: ' + str(rank) + ' \n Rank fore: ' + str(rank_fore)

            send_text = 'Coins new are: \n' + text
            send_message(text)


        time.sleep(100)



if __name__ == "__main__":
    main()

