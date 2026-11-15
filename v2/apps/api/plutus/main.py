import csv
import hashlib
import hmac
import io
import os
import secrets
import time
from contextlib import asynccontextmanager
from typing import Literal
from uuid import UUID
import httpx
from fastapi import FastAPI, Request, Response, HTTPException, Depends, Header
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field, ConfigDict
from sqlalchemy import select, insert, delete, text
from .db import metadata, engine_for, users, sessions, watchlist
from .accounting import initialize, execute, snapshot, DomainError, now, uid

class Credentials(BaseModel):
    email: str = Field(min_length=5, max_length=254, pattern=r'^[^\s@]+@[^\s@]+\.[^\s@]+$')
    password: str = Field(min_length=12, max_length=128)
class Symbol(BaseModel):
    symbol: str = Field(pattern=r'^(NSE|BSE):[A-Z0-9&._-]{1,24}$')
class Order(Symbol):
    model_config = ConfigDict(extra='forbid')
    side: Literal['BUY','SELL']
    quantity: int = Field(strict=True, gt=0, le=1000000)
    price: str = Field(max_length=20)
    confirmed: Literal[True]


def create_app(database_url=None, environment=None):
    env = environment or os.getenv('PLUTUS_ENV', 'production')
    url = database_url or os.getenv('DATABASE_URL')
    engine = engine_for(url) if url else None
    if env == 'production' and url and url.startswith('sqlite'): raise RuntimeError('Production requires PostgreSQL')
    supabase = os.getenv('SUPABASE_URL', '').rstrip('/')
    public_key = os.getenv('SUPABASE_PUBLISHABLE_KEY', '')
    origin = os.getenv('APP_ORIGIN', 'http://localhost:3000')
    @asynccontextmanager
    async def lifespan(app):
        if engine and env == 'development': metadata.create_all(engine)
        yield
        if engine: engine.dispose()
    app = FastAPI(title='Plutus AI 2.0', version='0.1.0', lifespan=lifespan)
    app.state.engine = engine
    buckets = {}
    @app.middleware('http')
    async def boundaries(request, call_next):
        if request.method not in ('GET','HEAD','OPTIONS') and request.headers.get('origin') != origin:
            return Response('Untrusted request origin', status_code=403)
        # Process-local development protection. Shared rate limiting is a production launch blocker.
        key = request.client.host if request.client else 'unknown'
        minute = int(time.time() // 60)
        key = (key, minute)
        buckets[key] = buckets.get(key, 0) + 1
        if len(buckets) > 10000:
            for old in list(buckets):
                if old[1] < minute: buckets.pop(old, None)
        if buckets[key] > 120: return Response('Rate limit exceeded', status_code=429)
        response = await call_next(request)
        response.headers['Cache-Control'] = 'no-store'
        response.headers['X-Content-Type-Options'] = 'nosniff'
        return response
    def database():
        if engine is None: raise HTTPException(503, 'Database is not configured')
        return engine
    def current_user(request: Request, db=Depends(database)):
        token = request.cookies.get('plutus_session')
        if not token: raise HTTPException(401, 'Sign in to continue')
        if env == 'development':
            with db.connect() as conn:
                row = conn.execute(select(sessions.c.user_id).where(sessions.c.digest == hashlib.sha256(token.encode()).hexdigest(), sessions.c.expires > int(time.time()))).first()
            if not row: raise HTTPException(401, 'Session expired')
            return row[0]
        if not supabase or not public_key: raise HTTPException(503, 'Supabase authentication is not configured')
        try:
            result = httpx.get(supabase + '/auth/v1/user', headers={'apikey': public_key, 'Authorization': 'Bearer ' + token}, timeout=10)
        except httpx.HTTPError: raise HTTPException(503, 'Authentication provider unavailable')
        if result.status_code != 200: raise HTTPException(401, 'Session expired')
        try: return str(UUID(result.json()['id']))
        except (ValueError, KeyError): raise HTTPException(502, 'Invalid authentication provider response')
    app.state.current_user = current_user
    def issue(response, token):
        response.set_cookie('plutus_session', token, httponly=True, secure=env != 'development', samesite='strict', max_age=3600, path='/')
    def password_hash(password, salt):
        return hashlib.pbkdf2_hmac('sha256', password.encode(), salt.encode(), 600000).hex()
    @app.get('/api/v1/health')
    def health():
        ready = False
        if engine:
            try:
                with engine.connect() as conn: conn.execute(select(users.c.id).limit(1))
                ready = True
            except Exception: pass
        return {'service': 'plutus-api', 'version': '0.1.0', 'database_ready': ready, 'environment': env, 'public_launch_ready': False}
    @app.get('/api/v1/capabilities')
    def capabilities():
        return {'auth': bool(engine and (env == 'development' or supabase and public_key)),
                'environment': env, 'market_data': False, 'live_trading': False, 'payments': False,
                'ai': False, 'forecasts': False, 'paper_mode': 'user_entered_scenario_prices',
                'paper_fee_bps': 10, 'currency': 'INR'}
    @app.post('/api/v1/auth/register')
    def register(body: Credentials, db=Depends(database)):
        email = body.email.lower()
        if env != 'development':
            if not supabase or not public_key: raise HTTPException(503, 'Supabase authentication is not configured')
            try:
                r = httpx.post(supabase + '/auth/v1/signup', headers={'apikey': public_key}, json={'email': email,'password': body.password}, timeout=10)
            except httpx.HTTPError: raise HTTPException(503, 'Authentication provider unavailable')
            if r.status_code not in (200,201): raise HTTPException(400, 'Registration could not be completed')
            return {'message': 'Check your email to verify your account.'}
        from sqlalchemy.exc import IntegrityError
        salt = secrets.token_hex(16)
        try:
            with db.begin() as conn: conn.execute(insert(users).values(id=uid(), email=email, password=salt + ':' + password_hash(body.password,salt)))
        except IntegrityError: raise HTTPException(400, 'Registration could not be completed')
        return {'message': 'Development account created. You can now sign in. Email verification is not enabled locally.'}
    @app.post('/api/v1/auth/login')
    def login(body: Credentials, response: Response, db=Depends(database)):
        if env != 'development':
            if not supabase or not public_key: raise HTTPException(503, 'Supabase authentication is not configured')
            try:
                r = httpx.post(supabase + '/auth/v1/token?grant_type=password', headers={'apikey': public_key}, json=body.model_dump(), timeout=10)
            except httpx.HTTPError: raise HTTPException(503, 'Authentication provider unavailable')
            if r.status_code != 200: raise HTTPException(401, 'Invalid credentials or unverified email')
            issue(response, r.json()['access_token'])
            return {'message':'Signed in'}
        with db.begin() as conn:
            row = conn.execute(select(users).where(users.c.email == body.email.lower())).mappings().first()
            salt, expected = row['password'].split(':') if row else ('invalid', '0' * 64)
            valid = hmac.compare_digest(password_hash(body.password, salt), expected)
            if not row or not valid: raise HTTPException(401, 'Invalid credentials')
            token = secrets.token_urlsafe(32)
            conn.execute(insert(sessions).values(digest=hashlib.sha256(token.encode()).hexdigest(), user_id=row['id'], expires=int(time.time())+3600))
        issue(response, token)
        return {'message':'Signed in'}
    @app.post('/api/v1/auth/logout')
    def logout(request: Request, response: Response, db=Depends(database)):
        token = request.cookies.get('plutus_session', '')
        if env == 'development':
            with db.begin() as conn: conn.execute(delete(sessions).where(sessions.c.digest == hashlib.sha256(token.encode()).hexdigest()))
        elif token and supabase and public_key:
            try:
                r = httpx.post(supabase + '/auth/v1/logout', headers={'apikey': public_key,'Authorization':'Bearer '+token},timeout=10)
                if r.status_code not in (200,204,401): raise HTTPException(503,'Session revocation failed; retry logout')
            except httpx.HTTPError: raise HTTPException(503,'Session revocation failed; retry logout')
        response.delete_cookie('plutus_session', path='/')
        return {'message':'Signed out'}
    @app.get('/api/v1/me')
    def me(user=Depends(current_user)): return {'id':user}
    @app.post('/api/v1/accounts/initialize')
    def init(user=Depends(current_user), db=Depends(database)):
        initialize(db,user)
        return {'message':'Manual portfolio and virtual account initialized'}
    @app.get('/api/v1/accounts/{kind}')
    def overview(kind: Literal['paper','manual'], user=Depends(current_user), db=Depends(database)):
        return snapshot(db,user,kind)
    @app.post('/api/v1/accounts/{kind}/orders')
    def order(kind: Literal['paper','manual'], body: Order, user=Depends(current_user), db=Depends(database), idempotency_key: str = Header(min_length=16, max_length=100)):
        try: return execute(db,user,kind,body.model_dump(exclude={'confirmed'}),idempotency_key)
        except DomainError as error: raise HTTPException(409,str(error))
    @app.get('/api/v1/accounts/{kind}/export')
    def export(kind: Literal['paper','manual'], user=Depends(current_user), db=Depends(database)):
        data = snapshot(db,user,kind)
        out=io.StringIO()
        writer=csv.writer(out)
        writer.writerow(['mode','id','symbol','side','quantity','price_INR','fees_INR','realized_INR','timestamp'])
        for o in data['orders']: writer.writerow([kind]+[o[k] for k in ('id','symbol','side','quantity','price','fee','realized','created')])
        return Response(out.getvalue(),media_type='text/csv',headers={'Content-Disposition':f'attachment; filename="plutus-{kind}.csv"'})
    @app.get('/api/v1/watchlist')
    def list_watch(user=Depends(current_user), db=Depends(database)):
        with db.connect() as conn: return [dict(r) for r in conn.execute(select(watchlist.c.symbol,watchlist.c.created).where(watchlist.c.user_id==user)).mappings()]
    @app.post('/api/v1/watchlist')
    def add_watch(body: Symbol,user=Depends(current_user),db=Depends(database)):
        from sqlalchemy.exc import IntegrityError
        try:
            with db.begin() as conn: conn.execute(insert(watchlist).values(user_id=user,symbol=body.symbol,created=now()))
        except IntegrityError: pass
        return {'symbol':body.symbol}
    @app.delete('/api/v1/watchlist/{symbol}')
    def remove_watch(symbol: str,user=Depends(current_user),db=Depends(database)):
        with db.begin() as conn: conn.execute(delete(watchlist).where(watchlist.c.user_id==user,watchlist.c.symbol==symbol))
        return {'message':'Removed'}
    @app.post('/api/v1/broker/orders')
    def live_order(user=Depends(current_user)):
        raise HTTPException(403,'Live execution is not implemented or authorized')
    return app
app = create_app()
