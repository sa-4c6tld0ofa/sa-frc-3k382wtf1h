# Copyright (c) 2018-present, Taatu Ltd.
#
# This source code is licensed under the MIT license found in the
# LICENSE file in the root directory of this source tree.
import sys
import os
import datetime
import time
from datetime import timedelta
import csv
from pathlib import Path
from model_arima_7d import *
from model_ma10 import *

pdir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(os.path.abspath(pdir) )
from settings import *
sett = sa_path()

sys.path.append(os.path.abspath( sett.get_path_pwd() ))
from sa_access import *
access_obj = sa_db_access()

sys.path.append(os.path.abspath(sett.get_path_core() ))
from ta_instr_sum import *
from ta_gen_chart_data import *
from get_frc_pnl import *
from get_trades import *

db_usr = access_obj.username(); db_pwd = access_obj.password(); db_name = access_obj.db_name(); db_srv = access_obj.db_server()

def clear_chart_data(s):
    try:
        import pymysql.cursors
        connection = pymysql.connect(host=db_srv,
                                     user=db_usr,
                                     password=db_pwd,
                                     db=db_name,
                                     charset='utf8mb4',
                                     cursorclass=pymysql.cursors.DictCursor)

        cr = connection.cursor(pymysql.cursors.SSCursor)
        sql = "DELETE FROM chart_data WHERE symbol = '"+ str(s) +"'"
        cr.execute(sql)
        connection.commit()

        cr.close()
        connection.close()
    except Exception as e: print(e)

def clear_trades(s):
    try:
        import pymysql.cursors
        connection = pymysql.connect(host=db_srv,
                                     user=db_usr,
                                     password=db_pwd,
                                     db=db_name,
                                     charset='utf8mb4',
                                     cursorclass=pymysql.cursors.DictCursor)

        cr = connection.cursor(pymysql.cursors.SSCursor)
        sql = "DELETE FROM trades WHERE symbol = '"+ str(s) +"'"
        cr.execute(sql)
        connection.commit()

        cr.close()
        connection.close()

    except Exception as e: print(e)

def get_instr_decimal_places(s):
    r = 5
    try:
        import pymysql.cursors
        connection = pymysql.connect(host=db_srv,
                                     user=db_usr,
                                     password=db_pwd,
                                     db=db_name,
                                     charset='utf8mb4',
                                     cursorclass=pymysql.cursors.DictCursor)

        cr = connection.cursor(pymysql.cursors.SSCursor)
        sql = "SELECT decimal_places FROM instruments WHERE symbol = '"+ str(s) +"'"
        cr.execute(sql)
        rs = cr.fetchall()
        for row in rs: r = row[0]

    except Exception as e: print("get_instr_decimal_places() " + str(e) )
    return r

def compute_target_price(uid,force_full_update):
    try:
        nd = 370
        dn = datetime.datetime.now() - timedelta(days=10)
        dn = dn.strftime("%Y%m%d")


        #name column of each model in the same order...
        selected_model_column = 'price_instruments_data.arima_7d_tp'
        ############################################################################################
        # (1) Add model column here define variables
        ############################################################################################
        column_of_each_model = 'instruments.score_arima_7d, instruments.score_ma10'
        score_arima_7d = 0
        score_ma10 = 0
        #------------------------------------------------------------------------------------------

        import pymysql.cursors
        connection = pymysql.connect(host=db_srv,
                                     user=db_usr,
                                     password=db_pwd,
                                     db=db_name,
                                     charset='utf8mb4',
                                     cursorclass=pymysql.cursors.DictCursor)

        cr = connection.cursor(pymysql.cursors.SSCursor)
        sql = "SELECT symbol from symbol_list WHERE uid = " + str(uid)
        cr.execute(sql)
        rs = cr.fetchall()
        for row in rs: symbol = row[0]

        sql = "SELECT asset_class, pip, " + str(column_of_each_model) + " FROM instruments JOIN symbol_list ON symbol_list.symbol = instruments.symbol WHERE symbol_list.uid = " + str(uid)
        cr.execute(sql)
        rs = cr.fetchall()
        for row in rs:
            asset_class = row[0]
            pip = row[1]
            ##########################################################################################
            # (2) Add model column as per column_of_each_model variable
            ##########################################################################################
            score_arima_7d = row[2]
            score_ma10 = row[3]
            #----------------------------------------------------------------------------------------


        #############################################################################################
        # (3) Add model to the model_list
        #############################################################################################
        model_list = (score_arima_7d, score_ma10)
        #--------------------------------------------------------------------------------------------
        selected_model_id = model_list.index( max(model_list) )

        ##############################################################################################
        # (4) Add model column in here for index
        ##############################################################################################
        if selected_model_id == 0: selected_model_column = 'price_instruments_data.arima_7d_tp'
        if selected_model_id == 1: selected_model_column = 'price_instruments_data.ma10_tp'
        #---------------------------------------------------------------------------------------------

        sql = "SELECT id FROM price_instruments_data WHERE symbol ='"+ symbol +"' ORDER BY date DESC LIMIT 1"
        cr.execute(sql)
        rs = cr.fetchall()
        price_id = 0
        for row in rs: price_id = row[0]

        if force_full_update:
            sql = "UPDATE price_instruments_data SET price_instruments_data.target_price = CAST("+ selected_model_column +" AS DECIMAL(20,"+ str( get_instr_decimal_places(symbol) ) +")) WHERE price_instruments_data.symbol = '"+ symbol + "'"
            print('### ::: ' + sql)
            cr.execute(sql); connection.commit()
            clear_chart_data(symbol)
            clear_trades(symbol)
            get_forecast_pnl(symbol,uid,nd)

            get_trades(symbol,uid,nd)
            gen_chart(symbol,uid)
            get_instr_sum(symbol,uid,asset_class,dn,pip)
        else:
            sql = "UPDATE price_instruments_data SET price_instruments_data.target_price = CAST("+ selected_model_column +" AS DECIMAL(20,"+ str( get_instr_decimal_places(symbol) ) +")) WHERE price_instruments_data.id = " + str(price_id)
            cr.execute(sql); connection.commit()


        cr.close()
        connection.close()


    except Exception as e: print("compute_target_price() " + str(e) )


def set_all_prediction_model_target_price_n_score(uid,force_full_update):
    try:
        #Set the score and return model_tp
        arima_7d_tp = set_model_arima_7d(uid,force_full_update)
        ma10_tp = set_model_ma10(uid,force_full_update)
        #target_price get the value of highest score model
        compute_target_price(uid,force_full_update)

    except Exception as e: print("set_all_prediction_model_target_price_n_score() " + str(e) )


def output_prediction(force_full_update,uid):
    try:

        import pymysql.cursors
        connection = pymysql.connect(host=db_srv,
                                     user=db_usr,
                                     password=db_pwd,
                                     db=db_name,
                                     charset='utf8mb4',
                                     cursorclass=pymysql.cursors.DictCursor)

        cr = connection.cursor(pymysql.cursors.SSCursor)

        if uid == 0:
            sql = "SELECT uid FROM symbol_list WHERE symbol NOT LIKE '%"+ get_portf_suffix() +"%' ORDER BY symbol"
        else:
            sql = "SELECT uid FROM symbol_list WHERE uid = " + str(uid)

        cr.execute(sql)
        rs = cr.fetchall()
        for row in rs:
            uid = row[0]
            set_all_prediction_model_target_price_n_score(uid,force_full_update)

        cr.close()
        connection.close()

    except Exception as e: print("output_prediction() " + str(e) )
