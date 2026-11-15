"""Offline research only. No probabilities or trading recommendations.

Usage: python -m research.evaluate licensed.csv --horizon 5 --source 'Vendor/dataset/version'
CSV columns: date, adjusted_close. One instrument, chronological daily trading sessions.
"""
import argparse
import hashlib
import json
from pathlib import Path
import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error

def features(prices, horizon):
    if horizon not in (1, 5, 20): raise ValueError('Supported horizons: 1, 5, 20 sessions')
    returns = prices.pct_change(fill_method=None)
    x = pd.DataFrame({f'return_lag_{lag}':returns.shift(lag) for lag in (0,1,2,5,10)})
    for window in (5,20,60):
        x[f'momentum_{window}'] = prices / prices.shift(window) - 1
        x[f'volatility_{window}'] = returns.rolling(window).std()
    y = prices.shift(-horizon) / prices - 1
    return x,y

def evaluate(frame, horizon, source):
    if not source.strip(): raise ValueError('A source identifier is required')
    dates = pd.to_datetime(frame['date'], errors='raise', utc=True)
    if not dates.is_monotonic_increasing or dates.duplicated().any(): raise ValueError('Dates must be unique and chronological')
    prices = pd.to_numeric(frame['adjusted_close'], errors='raise').reset_index(drop=True)
    if not np.isfinite(prices).all() or (prices<=0).any(): raise ValueError('Prices must be finite and positive')
    x,y = features(prices,horizon)
    valid = x.notna().all(axis=1) & y.notna()
    indices = np.flatnonzero(valid.to_numpy())
    if len(indices)<350: raise ValueError('At least 350 feature-complete labelled sessions are required')
    start=indices[250]
    prediction=[]; actual=[]; baselines=[]; audits=[]
    # Expanding window with a horizon purge: every training target ends BEFORE the test decision.
    for split in range(start,int(indices[-1])+1,20):
        train=indices[indices+horizon<split]
        test=indices[(indices>=split)&(indices<split+20)]
        if not len(test): continue
        model=HistGradientBoostingRegressor(max_iter=60,max_leaf_nodes=7,l2_regularization=5,random_state=42)
        model.fit(x.iloc[train],y.iloc[train])
        prediction.extend(model.predict(x.iloc[test]).tolist())
        actual.extend(y.iloc[test].tolist())
        baselines.extend([float(y.iloc[train].tail(60).mean())]*len(test))
        audits.append({'training_last_feature_index':int(train[-1]),'training_last_target_index':int(train[-1]+horizon),'test_first_index':int(test[0]),'test_last_index':int(test[-1])})
    actual=np.array(actual)
    def metrics(pred):
        pred=np.array(pred)
        return {'mae_return':float(mean_absolute_error(actual,pred)), 'rmse_return':float(mean_squared_error(actual,pred)**.5),
                'directional_accuracy':float(np.mean(np.sign(actual)==np.sign(pred)))}
    scores={'hist_gradient_boosting':metrics(prediction),'no_change':metrics(np.zeros(len(actual))),'trailing_mean_return':metrics(baselines)}
    return {'version':'research-v0.1','source':source,'horizon_sessions':horizon,'observations':len(prices),'out_of_sample_predictions':len(actual),
            'coverage':{'start':str(dates.iloc[0]),'end':str(dates.iloc[-1])},'metrics':scores,'folds':audits,
            'beats_both_baselines_mae':scores['hist_gradient_boosting']['mae_return']<min(scores['no_change']['mae_return'],scores['trailing_mean_return']['mae_return']),
            'deployment_eligible':False,'probabilities':None,'prediction_interval':None,
            'limitations':['Offline evaluation; not a validated production forecasting service.','Overlapping horizon labels produce correlated errors.','No point-in-time corporate action or licensing validation is automatic.','No economic profitability or trading-cost evaluation.','No calibrated probabilities, intervals, drift monitoring or model registry yet.']}

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('csv',type=Path);p.add_argument('--horizon',type=int,choices=[1,5,20],default=5);p.add_argument('--source',required=True);args=p.parse_args()
    frame=pd.read_csv(args.csv)
    result=evaluate(frame,args.horizon,args.source)
    result['dataset_sha256']=hashlib.sha256(args.csv.read_bytes()).hexdigest()
    print(json.dumps(result,indent=2,allow_nan=False))
