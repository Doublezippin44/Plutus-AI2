"""Private application tables. Cash and pooled position costs are integer paise."""
import os
from sqlalchemy import (create_engine, MetaData, Table, Column, String, Integer,
                        BigInteger, ForeignKey, UniqueConstraint, CheckConstraint, Text)
metadata = MetaData()
users = Table('plutus_users', metadata,
    Column('id', String, primary_key=True), Column('email', String, unique=True, nullable=False),
    Column('password', String, nullable=False))
sessions = Table('plutus_sessions', metadata,
    Column('digest', String, primary_key=True), Column('user_id', String, ForeignKey(users.c.id), nullable=False),
    Column('expires', BigInteger, nullable=False))
accounts = Table('plutus_accounts', metadata,
    Column('id', String, primary_key=True), Column('user_id', String, nullable=False, index=True),
    Column('kind', String, nullable=False), Column('cash', BigInteger, nullable=False),
    UniqueConstraint('user_id', 'kind'), CheckConstraint("kind IN ('paper','manual')"), CheckConstraint('cash >= 0'))
positions = Table('plutus_positions', metadata,
    Column('account_id', String, ForeignKey(accounts.c.id), primary_key=True),
    Column('symbol', String, primary_key=True), Column('quantity', Integer, nullable=False),
    Column('cost', BigInteger, nullable=False), CheckConstraint('quantity >= 0'), CheckConstraint('cost >= 0'))
orders = Table('plutus_orders', metadata,
    Column('id', String, primary_key=True), Column('account_id', String, ForeignKey(accounts.c.id), nullable=False, index=True),
    Column('request_key', String, nullable=False), Column('fingerprint', String, nullable=False),
    Column('symbol', String, nullable=False), Column('side', String, nullable=False),
    Column('quantity', Integer, nullable=False), Column('price', BigInteger, nullable=False),
    Column('fee', BigInteger, nullable=False), Column('realized', BigInteger, nullable=False),
    Column('created', String, nullable=False), Column('cash_after', BigInteger, nullable=False),
    UniqueConstraint('account_id', 'request_key'), CheckConstraint("side IN ('BUY','SELL')"))
ledger = Table('plutus_ledger', metadata,
    Column('id', String, primary_key=True), Column('account_id', String, ForeignKey(accounts.c.id), nullable=False, index=True),
    Column('order_id', String, ForeignKey(orders.c.id), unique=True), Column('delta', BigInteger, nullable=False),
    Column('reason', String, nullable=False), Column('created', String, nullable=False))
watchlist = Table('plutus_watchlist', metadata,
    Column('user_id', String, primary_key=True), Column('symbol', String, primary_key=True),
    Column('created', String, nullable=False))

def engine_for(url):
    args = {'connect_args': {'check_same_thread': False, 'timeout': 30}} if url.startswith('sqlite') else {}
    return create_engine(url, pool_pre_ping=True, **args)
