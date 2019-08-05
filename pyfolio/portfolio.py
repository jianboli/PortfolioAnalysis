import numpy as np
import statsmodels.api as sm
import pandas as pd


def cumpound_pnl(r):
    return (r+1).product()-1

def format_pnl(pnl_s):
    """
    Construct the performance table from given monthly P&L
    pnl_s: monthly returns as pandas data seriers with index the monthly end dates
    """
    pnl_df = pd.DataFrame({"Monthly_End":pnl_s.index, "P&L":pnl_s.values})
    pnl_df['Year'] = pnl_df['Monthly_End'].dt.year
    pnl_df['Month'] = pnl_df['Monthly_End'].dt.month

    pnl_df_pivot = pnl_df.pivot(index="Month", columns='Year', values='P&L')
    pnl_yearly = pnl_df.groupby('Year').agg({'P&L': cumpound_pnl})
    pnl_yearly.columns=["Yearly"]
    pnl_yearly_cum = (pnl_yearly+1).cumprod()-1
    pnl_yearly_cum.columns = ["Cumulative"]
    pnl_df_pivot = pnl_df_pivot.append(pnl_yearly.T)
    pnl_df_pivot = pnl_df_pivot.append(pnl_yearly_cum.T)
    return pnl_df_pivot
    
def mdd(r):
    cum = (r+1).cumprod()
    peak = cum.cummax()
    dd = -(cum/peak-1)
    return dd.max()

def calc_net_performance(gross_perf, management_fee, incentive_fee):
    """
    Calucate monthly net after incentive_fee and management_fee. Most common configuration:
    - high water mark, no clawbacks
    - incentive fee is applied on the performance (no benchmark based performance)
    :param gross_perf: the pandas data series/table contains monthly gross performance with monthly end date as index
    :param management_fee: management fee ratio
    :param incentive_fee: incentive fee
    :return: the net performance as data Series after all the fees
    """
    # make sure the gross is a series
    if isinstance(gross_perf, pd.DataFrame):
        gross_perf = gross_perf.iloc[:, 0]

    # make sure the index is datetime
    gross_perf.index = pd.to_datetime(gross_perf.index)
    gross_perf.sort_index()
    prev_months_cumulative = 0
    prev_ytd = 0
    dec_ytd = 0
    high_water_mark = 0

    net = list()
    for dt, gr in gross_perf.iteritems():
        new_months_cumulative = (gr + 1) * (prev_months_cumulative + 1) - 1
        management_fee_month = (prev_months_cumulative + 1) * (management_fee / 12)

        if dt.month == 1:
            dec_ytd = prev_months_cumulative
            if dec_ytd > high_water_mark:
                high_water_mark = dec_ytd

        new_cummulative_after_management = new_months_cumulative - management_fee_month

        # Calculated YTD Management for YTDPerformance Calculation
        ytd_managemnt = (new_cummulative_after_management + 1) / (dec_ytd + 1) - 1

        # Only charge performance when (new_cummulative_after_management - high_water_mark) > 0 i.e WaterMark exceed previous year
        if incentive_fee > 0 and new_cummulative_after_management > high_water_mark:
            ytd_performance = ytd_managemnt - (incentive_fee * (1 + ytd_managemnt) * ((new_cummulative_after_management - high_water_mark) / (1 + new_cummulative_after_management)))
        else:
            ytd_performance = ytd_managemnt

        if dt.month == 1:
            monthly_net = ytd_performance
        else:
            monthly_net = (1 + ytd_performance) / (1 + prev_ytd) - 1

        net.append(monthly_net)
        prev_months_cumulative = new_cummulative_after_management
        prev_ytd = ytd_performance

    return pd.Series(net, index=gross_perf.index)


def statistics(r, b=None, rf=None, freq=12):
    """
    Generate the portfolio return matrix from the monthly P&L including the following:
        Total return:
        Annual Return:
        Volatility
        Sharpe Ratio
        Percentage Positive Month/Day
        MDD
        Skewness
        Kurtosis
    If b is supplied then the following will be included
        Information Ratio
        Correlation with Bechmark
        Alpah (Non Aunnalized)
        Beta
    """
    stat = []
    trr = (r+1).product()-1
    n = float(len(r))
    vol = r.std()
    
    if rf is None:
        rf = 0
        
    stat.append(('Total Return', trr))
    stat.append(('Annual Return', (1+trr)**(freq/n)-1))
    stat.append(("Volatility", vol*np.sqrt(freq)))
    stat.append(('Sharp Ratio', (r.values-rf.values).mean()/vol*np.sqrt(freq)))
    stat.append(('Percentage Positive Month', (r>0).sum()/n))
    stat.append(('MDD', mdd(r)))
    stat.append(('Skewness', r.skew()))
    stat.append(('Kurtosis', r.kurtosis()))
    
    if b is not None:
        ex_return = r.values-b.values
        stat.append(('Information Ratio', ex_return.mean()/ex_return.std()*np.sqrt(freq)))
        stat.append(('Correlation with Bechmark', np.corrcoef(r, b)[0, 1]))

        X = sm.add_constant(b.values)
        param = sm.OLS(r.values, X).fit().params

        stat.append(('Alpah (Non Aunnalized)', param[0]))
        stat.append(('Beta', param[1]))

    df = pd.DataFrame(stat, columns=['Summary', 'Stat'])
    return df


if __name__ == "__main__":
    test_net_fee = True
    if test_net_fee:
        gross = pd.DataFrame(data = [0.034107741833528, -0.00833852885640296, 0.0320612695430027, 0.0102631014311665, 0.0113370205823213, 0.0180773838954622,
                            0.047031427894648, 0.00295545925707486, 0.0324885986089885, 0.00865585089499699, 0.00346117358058629, 0.0081528599398073, 0.0148837779649957,
                            -0.00418473351008752, 0.056113255346828, 0.0205687580374805, -0.0142217587735437, 0.00766906087868691, 0.0235982274548432, -0.00915881701770105,
                            0.0139498718873998, 0.00555486136711258,  0.0066962328677207, -0.000910732639986089, -0.00497602777657502, 0.00174304734261033, 0.00619146958299455,
                            0.024184586, 0.036688053066313, 0.0115983334056298, 0.0214857037577827, 0.00458691255044807, 0.00655048461181207],
                           index=["30-Nov-2016", "30-Dec-2016", "31-Jan-2017", "28-Feb-2017", "31-Mar-2017", "28-Apr-2017", "31-May-2017", "30-Jun-2017", "31-Jul-2017", "31-Aug-2017",
                                  "29-Sep-2017", "31-Oct-2017", "30-Nov-2017", "29-Dec-2017", "31-Jan-2018", "28-Feb-2018", "31-Mar-2018", "30-Apr-2018", "31-May-2018", "30-Jun-2018", "31-Jul-2018", "31-Aug-2018",
                                  "30-Sep-2018", "31-Oct-2018", "30-Nov-2018", "31-Dec-2018", "31-Jan-2019", "28-Feb-2019", "31-Mar-2019", "30-Apr-2019", "31-May-2019", "30-Jun-2019", "31-Jul-2019"])
        gross.index = pd.to_datetime(gross.index, format="%d-%b-%Y")
        net = calc_net_performance(gross, 0.01, 0.1)
        print("Cumulative Net: {}".format((net+1).product() - 1))
        assert np.abs((net+1).product() - 1 -  0.429888256) < 1e-6, "The Net fee calcuation does not look right!"

        pass