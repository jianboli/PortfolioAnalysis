from tia.bbg import LocalTerminal
import datetime
import numpy as np

def _get_memb_direct(index_ticker, as_of_date):
    memb = LocalTerminal.get_reference_data(index_ticker, "INDX_MWEIGHT_HIST", END_DATE_OVERRIDE=as_of_date)
    memb = memb.as_frame()
    memb = memb["INDX_MWEIGHT_HIST"].iloc[0]
    memb.columns = ['Ticker', 'Weight']
    memb['Ticker'] = memb['Ticker'] + " Equity"
    return memb

def _simu_memb_weight(ticker_list, as_of_date):
    mkt_cap = LocalTerminal.get_historical(ticker_list, "CUR_MKT_CAP", 
                                           as_of_date, 
                                           as_of_date, 
                                           EQY_FUND_CRNCY='EUR').as_frame()
    
    mkt_cap = mkt_cap.stack(level=0)
    mkt_cap.index = mkt_cap.index.droplevel(0)
    mkt_cap['Weight_est'] = mkt_cap['CUR_MKT_CAP']/mkt_cap['CUR_MKT_CAP'].sum()*100
    return mkt_cap
    

def get_memb(index_ticker, as_of_date=None, est_wgt_if_null=False, as_of_business_date = None):
    """
	Read the index member weight. If the member is not aviable, estimate based on market capital
    :param index_ticker: Bloomberg Ticker of the index
    :param as_of_date: The date the member is based on. If none, use today
    :param est_wgt_if_null: If the member is missing/not available, estimate from market captial
    :param as_of_business_date: the latest business date as of as_of_date. This is used to get the market calpital. If None, as_of_date will be used
    :return: A pandas DataFrame with columns [Ticker, Weight]
    """

    if as_of_date == None:
        as_of_date = datetime.datetime.today()

    if as_of_business_date == None:
        as_of_business_date = as_of_date

    as_of_date = as_of_date.strftime('%Y%m%d')
    memb = _get_memb_direct(index_ticker, as_of_date)
    if((memb['Weight'] < 0).all() or memb['Weight'].isna().all()): # Assume it is capital weighted
        if est_wgt_if_null:
            memb_wgt = _simu_memb_weight(memb['Ticker'], as_of_business_date)
            memb = memb.merge(memb_wgt, how='left', left_on='Ticker', right_index=True)
            memb['Weight'] = memb['Weight_est']
            del memb['Weight_est']
            del memb['CUR_MKT_CAP']
        else:
            memb['Weight'] = np.nan

    memb['Weight'] = memb['Weight']/100.
    
    return memb

if __name__ == "__main__":
    idx = get_memb("SPX Index", est_wgt_if_null=True)

    print(idx.head())