# coding: utf-8

import numpy as np
import pandas as pd
#import matplotlib.pylab as plt
from datetime import datetime
from enum import Enum

from tia.bbg import LocalTerminal

class AdjMode(Enum):
    PX_LAST = 0
    NET = 1
    GROSS = 2

class Periodicity(Enum):
    DAILY = 0
    WEEKLY = 1
    MONTHLY = 2
    YEARLY = 3

def get_security_hist(tickers, st_date, ed_date, adj_mode=AdjMode.PX_LAST,
                      additional_fields=None, periodicity=Periodicity.MONTHLY):
    """
    This function is a wrapper of the LocalTerminal.get_historical function inside tia.
    :param tickers: The given security list
    :param st_date: the starting point of the period
    :param ed_date: the end point of the period
    :param adj_mode: dvd adjusted mode. If PX_LAST is supplied, whatever Bloomberg setting will be applied. Check DPDF {<GO>} for more details
    :param additional_fields: A list of additional fields that would like to be queried
    :param periodicity: Frequency of the data that will be returned
    :return: the data got from Bloomberg
    """

    if additional_fields is None:
        additional_fields = []

    if adj_mode == AdjMode.PX_LAST:
        field = ["PX_LAST"]
    elif adj_mode == AdjMode.NET:
        field = ["TOT_RETURN_INDEX_NET_DVDS"]
    else:
        field = ["TOT_RETURN_INDEX_GROSS_DVDS"]

    hist = LocalTerminal.get_historical(
        tickers,
        field + additional_fields,
        start=st_date,
        end=ed_date,
        period=periodicity.name
    )

    return hist.as_frame()

def get_period_return(ptf, st_date, ed_date, currency=None):
    """
    Calculate the periodic return of the given portfolio from the rebalance date til the end date
    :param ptf: A DataFrame with a single column DtdPNL ptf (DataFrame): columns contain "Security", "Weight"
    :param st_date: the rebalance date (single value) the date the portfolio starts
    :param ed_date: the date of the end calculation
    :param currency: the currency the performance is based on. If None, then local
    :return: the periodic returns of the given portfolio index by the EdDate and the calculation details
    """
    st_date = pd.to_datetime(st_date)
    ed_date = pd.to_datetime(ed_date)

    if currency is None:
        df = LocalTerminal.get_reference_data(ptf.loc[:, 'Security'], "CUST_TRR_RETURN_HOLDING_PER",
                                 CUST_TRR_START_DT=pd.to_datetime(st_date).strftime("%Y%m%d"),
                                 CUST_TRR_END_DT=pd.to_datetime(ed_date).strftime("%Y%m%d"))
    else:
        df = LocalTerminal.get_reference_data(ptf.loc[:, 'Security'], "CUST_TRR_RETURN_HOLDING_PER",
                                 CUST_TRR_START_DT=pd.to_datetime(st_date).strftime("%Y%m%d"),
                                 CUST_TRR_END_DT=pd.to_datetime(ed_date).strftime("%Y%m%d"),
                                 CUST_TRR_CRNCY=currency)
    df = df.as_frame()
    df['StDate'] = st_date
    df['EdDate'] = ed_date
    df['CUST_TRR_RETURN_HOLDING_PER'] = df['CUST_TRR_RETURN_HOLDING_PER']/100 # PNL is in the unit of percentage points
    df.reset_index(inplace=True)
    df.rename(columns={'CUST_TRR_RETURN_HOLDING_PER': "PNL", "index": "Ticker"}, inplace=True)

    # get the period to date return
    tot = pd.merge(ptf, df, left_on="Security", right_on="Ticker")

    tot['TotalReturn'] = tot["Weight"] * tot["PNL"]
    rtn = tot.groupby("EdDate").agg({"TotalReturn": "sum"})

    return rtn[['TotalReturn']], tot


def get_daily_return(ptf, st_date, ed_date, currency=None):
    """
    Calculate the daily return of the given portfolio from the rebalanced date til the end date. Note this method is
        resource EXPENSIVE as it relay on Bloomberg period return and then back calculate the daily return.
    :param ptf: A DataFrame with a single column DtdPNL ptf (DataFrame): columns contain "Security", "Weight", "Date".
    :param st_date: the rebalance date (single value) the date the portfolio starts
    :param ed_date: the date of the end calculation
    :param currency: the currency the performance is based on. If None, then local
    :return: a tuple of daily returns that of the given portfolio and position
    """

    st_date = pd.to_datetime(st_date)
    ed_date = pd.to_datetime(ed_date)
    dts = pd.date_range(st_date, end=ed_date, freq='D')[1:]  # rebalance date does not generate pnl
    dfs = pd.DataFrame()
    for dt in dts:  # get total pnl for each day
        if currency is None:
            df = LocalTerminal.get_reference_data(ptf.loc[:, 'Security'],
                 "CUST_TRR_RETURN_HOLDING_PER",
                  CUST_TRR_START_DT=pd.to_datetime(st_date).strftime("%Y%m%d"),
                  CUST_TRR_END_DT=pd.to_datetime(dt).strftime("%Y%m%d"))
        else:
            df = LocalTerminal.get_reference_data(ptf.loc[:, 'Security'],
                "CUST_TRR_RETURN_HOLDING_PER",
                 CUST_TRR_START_DT=pd.to_datetime(st_date).strftime("%Y%m%d"),
                 CUST_TRR_END_DT=pd.to_datetime(dt).strftime("%Y%m%d"),
                 CUST_TRR_CRNCY=currency)
        df = df.as_frame()
        df['EdDate'] = dt
        df['CUST_TRR_RETURN_HOLDING_PER'] = df['CUST_TRR_RETURN_HOLDING_PER'] / 100  # PNL is in the unit of percentage points
        df.reset_index(inplace=True)
        df.rename(columns={'CUST_TRR_RETURN_HOLDING_PER': "PNL", "index": "Ticker"}, inplace=True)
        dfs = dfs.append(df)

    # get the period to date return
    tot = pd.merge(ptf, dfs, left_on="Security", right_on="Ticker")
    tot['TotalReturn'] = tot["Weight"] * tot["PNL"]
    daily_return = tot.groupby("EdDate").agg({"TotalReturn": "sum"})

    # back calculate the daily return
    daily_return['StDate'] = st_date
    daily_return['YestTotalReturn'] = daily_return['TotalReturn'].shift(1)
    daily_return['DtdPNL'] = (daily_return['TotalReturn'] + 1) / (1 + daily_return['YestTotalReturn']) - 1
    daily_return.iloc[0, daily_return.columns.get_loc('DtdPNL')] = daily_return.iloc[
        0, daily_return.columns.get_loc('TotalReturn')]
    return daily_return[['DtdPNL']], tot
	


if __name__ == "__main__":


    ptf = pd.DataFrame(zip(['IBM US Equity', 'AAPL US Equity', 'GOOGL US Equity', 'FB US Equity'],
                       np.repeat(0.25, 4)), columns=["Security", "Weight"])

    # get the rebalance date
    ed_date = pd.to_datetime('2019-05-31')
    rebalance_dt = pd.to_datetime('2019-04-30')

    sec_hist = get_security_hist(ptf['Security'], rebalance_dt, ed_date, AdjMode.NET, ['PX_LAST'])
    print(sec_hist.head())

    perf, tot = get_daily_return(ptf, rebalance_dt, ed_date)

    print(perf)
    print(tot.head())

