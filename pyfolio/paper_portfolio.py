# coding: utf-8

import numpy as np
import pandas as pd
#import matplotlib.pylab as plt
import tia.bbg.datamgr as dm
from datetime import timedelta

import tia.bbg.datamgr as dm


def get_period_return(ptf, ed_date):
    """
    Args:
        ptf (DataFrame): columns contain "Security", "Weight", "Date".
             "Date" column should contains the rebalance date (single value) only
        rebalance_date (datetime64): the date the portfolio is rebalanced
        ed_date (datetime64): the date of the end calculation
    Returns:
        A DataFrame with a single column DtdPNL represend that of the given portfolio
    """

    mgr = dm.BbgDataManager()

    sids = mgr[ptf.loc[:, 'Security']]
    rebalance_date = ptf.iloc[0, ptf.columns.get_loc("Date")]
    dts = pd.date_range(rebalance_date, end=ed_date, fre='D')[1:]  # rebalance date does not generate pnl
    dfs = pd.DataFrame()
    for dt in dts:  # get total pnl for each day
        df = sids.get_attributes("CUST_TRR_RETURN_HOLDING_PER",
                                 CUST_TRR_START_DT=pd.to_datetime(rebalance_date).strftime("%Y%m%d"),
                                 CUST_TRR_END_DT=pd.to_datetime(dt).strftime("%Y%m%d"),
                                 CUST_TRR_CRNCY="USD")
        df['StDate'] = rebalance_date
        df['EdDate'] = dt
        df['CUST_TRR_RETURN_HOLDING_PER'] = df[
                                                'CUST_TRR_RETURN_HOLDING_PER'] / 100  # PNL is in the unit of percentage points
        df.reset_index(inplace=True)
        df.rename(columns={'CUST_TRR_RETURN_HOLDING_PER': "PNL", "index": "Ticker"}, inplace=True)
        dfs = dfs.append(df)

    # get the period to date return
    tot = pd.merge(ptf, dfs, left_on=("Security", "Date"), right_on=("Ticker", "StDate"))
    tot['TotalReturn'] = tot["Weight"] * tot["PNL"]
    daily_return = tot.groupby("EdDate").agg({"TotalReturn": "sum"})

    # back calculate the daily return
    daily_return['YestTotalReturn'] = daily_return['TotalReturn'].shift(1)
    daily_return['DtdPNL'] = (daily_return['TotalReturn'] + 1) / (1 + daily_return['YestTotalReturn']) - 1
    daily_return.iloc[0, daily_return.columns.get_loc('DtdPNL')] = daily_return.iloc[
        0, daily_return.columns.get_loc('TotalReturn')]
    return (daily_return[['DtdPNL']], tot)
	


if __name__ == "__main__":
    ptf = pd.read_excel("OPI.xls")
    ptf['Date'] = pd.to_datetime(ptf['Date'])
    # ptf['Weight'] = ptf['Weight'] * 2  # 2x gross

    # check the exposure
    gross = ptf.groupby("Date").agg({"Weight": lambda x: sum(abs(x))})
    gross.plot()

    # get the rebalance date
    rebalance_dt = ptf['Date'].unique()
    ptf.loc[ptf['Date'] == rebalance_dt[1], 'Security'].values
    daily_return = pd.DataFrame()
    tot = pd.DataFrame()
    for i in range(len(rebalance_dt) - 1):
        xx, yy = get_period_return(ptf.loc[ptf['Date'] == rebalance_dt[i], :], rebalance_dt[i + 1])
        daily_return = daily_return.append(xx)
        tot = tot.append(yy)

    daily_return.to_csv("DailyPNL.csv")

