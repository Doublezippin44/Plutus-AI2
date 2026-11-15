from concurrent.futures import ThreadPoolExecutor
import tempfile
from pathlib import Path
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select, func
from plutus.main import create_app
from plutus.db import ledger, accounts, orders
from plutus.accounting import initialize,execute,snapshot,DomainError

@pytest.fixture
def client(tmp_path):
    app=create_app('sqlite:///'+str(tmp_path/'test.db'),'development')
    with TestClient(app,headers={'origin':'http://localhost:3000'}) as c: yield c

def sign_in(c,email='one@example.com'):
    data={'email':email,'password':'A-long-test-password-123'}
    assert c.post('/api/v1/auth/register',json=data).status_code==200
    assert c.post('/api/v1/auth/login',json=data).status_code==200
    return c.get('/api/v1/me').json()['id']

def trade(c,side='BUY',qty=10,price='100.00',key='test-request-key-0001',kind='paper'):
    return c.post(f'/api/v1/accounts/{kind}/orders',headers={'Idempotency-Key':key},json={'symbol':'NSE:TCS','side':side,'quantity':qty,'price':price,'confirmed':True})

def test_auth_isolation_logout(client):
    assert client.get('/api/v1/accounts/paper').status_code==401
    sign_in(client)
    assert trade(client).status_code==200
    client.post('/api/v1/watchlist',json={'symbol':'NSE:TCS'})
    old=client.cookies.get('plutus_session')
    client.post('/api/v1/auth/logout')
    client.cookies.set('plutus_session',old)
    assert client.get('/api/v1/me').status_code==401
    client.cookies.clear()
    sign_in(client,'two@example.com')
    assert client.get('/api/v1/watchlist').json()==[]
    assert client.get('/api/v1/accounts/paper').json()['orders']==[]

def test_ledger_round_trip_and_idempotency(client):
    sign_in(client)
    assert trade(client).status_code==200
    first=trade(client).json()
    assert len(client.get('/api/v1/accounts/paper').json()['orders'])==1
    assert trade(client,qty=9).status_code==409
    assert trade(client,'SELL',10,'120.00','test-request-key-0002').json()['realized']=='197.80'
    account=client.get('/api/v1/accounts/paper').json()
    assert account['cash']=='1000197.80'
    assert account['positions']==[]
    with client.app.state.engine.connect() as conn:
        assert conn.execute(select(func.sum(ledger.c.delta))).scalar_one()==100019780
    assert client.get('/api/v1/accounts/paper/export').status_code==200

def test_rejections_atomicity(client):
    sign_in(client)
    for kwargs in [{'price':'not-a-number'},{'price':'NaN'},{'price':'Infinity'},{'price':'0.001'},{'price':'-1'},{'qty':1000000},{'side':'SELL'}]:
        assert trade(client,**kwargs).status_code==409
    assert client.get('/api/v1/accounts/paper').json()['orders']==[]
    assert client.post('/api/v1/accounts/initialize',headers={'Origin':'https://evil.test'}).status_code==403
    assert client.post('/api/v1/broker/orders').status_code==403

def test_partial_sale_and_manual_separation(client):
    sign_in(client)
    assert trade(client,kind='manual',qty=3,price='100.01').status_code==200
    assert trade(client,'SELL',1,'110.01','test-request-key-0002','manual').json()['realized']=='10.00'
    assert client.get('/api/v1/accounts/manual').json()['cost_basis']=='200.02'
    assert client.get('/api/v1/accounts/paper').json()['positions']==[]

def test_concurrent_duplicate_and_overspend(client):
    user=sign_in(client); engine=client.app.state.engine
    initialize(engine,user)
    body={'symbol':'NSE:TCS','side':'BUY','quantity':1,'price':'600000.00'}
    def run(key):
        try: return execute(engine,user,'paper',body,key)
        except DomainError:return None
    with ThreadPoolExecutor(max_workers=2) as pool:
        results=list(pool.map(run,['same-idempotency-key','same-idempotency-key']))
    assert results[0]['id']==results[1]['id']
    assert run('different-request-key') is None
    assert snapshot(engine,user,'paper')['cash']=='399400.00'

def test_production_fails_closed():
    with pytest.raises(RuntimeError): create_app('sqlite:///unsafe.db','production')
    with TestClient(create_app(environment='production')) as c:
        assert c.get('/api/v1/health').json()['public_launch_ready'] is False
        assert c.get('/api/v1/me').status_code==503
