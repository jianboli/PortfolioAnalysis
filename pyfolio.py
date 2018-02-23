def cumpond_pnl(r):
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
    pnl_yearly = pnl_df.groupby('Year').agg({'P&L': cumpond_pnl})
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
    return(dd.max())

def statitics(r, b=None, rf=None, freq=12):
    """
    Generate the portfolio return matrix from the monthly P&L including the following:
        Total return:
        Annual Return:
        Volatility
        Sharpe Ratio
        Percentage Positive Month/Day
        MDD
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
    stat.append(('Sharp Ratio', (r-rf).mean()/vol*np.sqrt(freq)))
    stat.append(('Percentage Positive Month', (r>0).sum()/n))
    stat.append(('MDD', mdd(r)))
    if b is not None:
        raise NotImplementedError("To be implemented")
        
    df = pd.DataFrame(stat, columns=['Label', 'Stat']).set_index('Label')
    return df['Stat']
