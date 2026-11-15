from contextlib import contextmanager
from datetime import datetime, timezone
from decimal import Decimal, ROUND_HALF_UP, InvalidOperation
import hashlib
import json
import uuid
from sqlalchemy import select, insert, update, func
from .db import accounts, positions, orders, ledger

class DomainError(ValueError): pass

def now(): return datetime.now(timezone.utc).isoformat()
def uid(): return str(uuid.uuid4())
def paise(value):
    try: value = Decimal(str(value))
    except InvalidOperation: raise DomainError("Invalid price")
    if not value.is_finite() or value <= 0 or value > Decimal('10000000') or value != value.quantize(Decimal('.01')):
        raise DomainError('Enter a positive price with at most two decimal places, up to ₹1 crore.')
    return int(value * 100)
def money(value): return f'{Decimal(value) / 100:.2f}'

@contextmanager
def transaction(engine):
    with engine.connect() as conn:
        if engine.dialect.name == 'sqlite': conn.exec_driver_sql('BEGIN IMMEDIATE')
        else: conn.begin()
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise

def account_for(conn, user, kind, create=False):
    row = conn.execute(select(accounts).where(accounts.c.user_id == user, accounts.c.kind == kind).with_for_update()).mappings().first()
    if row or not create: return row
    # PostgreSQL advisory transaction lock serializes first-account creation per user/kind.
    if conn.dialect.name == 'postgresql':
        from sqlalchemy import text
        conn.execute(text('SELECT pg_advisory_xact_lock(hashtext(:key))'), {'key': user + ':' + kind})
        row = conn.execute(select(accounts).where(accounts.c.user_id == user, accounts.c.kind == kind).with_for_update()).mappings().first()
        if row: return row
    amount = 100000000 if kind == 'paper' else 0
    row = {'id': uid(), 'user_id': user, 'kind': kind, 'cash': amount}
    conn.execute(insert(accounts).values(**row))
    if kind == 'paper':
        conn.execute(insert(ledger).values(id=uid(), account_id=row['id'], delta=amount, reason='VIRTUAL_CAPITAL', created=now()))
    return row

def initialize(engine, user):
    with transaction(engine) as conn:
        for kind in ('paper', 'manual'): account_for(conn, user, kind, True)

def execute(engine, user, kind, body, request_key):
    price = paise(body['price'])
    qty, side, symbol = body['quantity'], body['side'], body['symbol']
    if type(qty) is not int or not 1 <= qty <= 1000000: raise DomainError('Invalid quantity')
    if side not in ('BUY', 'SELL'): raise DomainError('Invalid side')
    fingerprint = hashlib.sha256(json.dumps({**body, 'price': price}, sort_keys=True).encode()).hexdigest()
    with transaction(engine) as conn:
        account = account_for(conn, user, kind, True)
        previous = conn.execute(select(orders).where(orders.c.account_id == account['id'], orders.c.request_key == request_key)).mappings().first()
        if previous:
            if previous['fingerprint'] != fingerprint: raise DomainError('Idempotency key already used for another order')
            return present_order(previous)
        position = conn.execute(select(positions).where(positions.c.account_id == account['id'], positions.c.symbol == symbol)).mappings().first()
        held, cost = (position['quantity'], position['cost']) if position else (0, 0)
        gross = qty * price
        # Explicit simulation assumption: 10 basis points each side, rounded half up.
        fee = int((Decimal(gross) / 1000).quantize(Decimal('1'), rounding=ROUND_HALF_UP)) if kind == 'paper' else 0
        realized = 0
        if side == 'BUY':
            delta = -(gross + fee)
            if kind == 'paper' and account['cash'] + delta < 0: raise DomainError('Insufficient virtual cash')
            new_qty, new_cost = held + qty, cost + gross + fee
        else:
            if qty > held: raise DomainError('Insufficient shares; short selling is not supported')
            allocated = cost if qty == held else int((Decimal(cost) * qty / held).quantize(Decimal('1'), rounding=ROUND_HALF_UP))
            delta, realized = gross - fee, gross - fee - allocated
            new_qty, new_cost = held - qty, cost - allocated
        cash_after = account['cash'] + delta if kind == 'paper' else 0
        if position:
            conn.execute(update(positions).where(positions.c.account_id == account['id'], positions.c.symbol == symbol).values(quantity=new_qty, cost=new_cost))
        else: conn.execute(insert(positions).values(account_id=account['id'], symbol=symbol, quantity=new_qty, cost=new_cost))
        conn.execute(update(accounts).where(accounts.c.id == account['id']).values(cash=cash_after))
        order = dict(id=uid(), account_id=account['id'], request_key=request_key, fingerprint=fingerprint,
                     symbol=symbol, side=side, quantity=qty, price=price, fee=fee, realized=realized, created=now(), cash_after=cash_after)
        conn.execute(insert(orders).values(**order))
        if kind == 'paper': conn.execute(insert(ledger).values(id=uid(), account_id=account['id'], order_id=order['id'], delta=delta, reason=side, created=order['created']))
        return present_order(order)

def present_order(row):
    return {**{k: row[k] for k in ('id','symbol','side','quantity','created')},
            **{k: money(row[k]) for k in ('price','fee','realized','cash_after')}, 'status': 'RECORDED'}

def snapshot(engine, user, kind):
    with engine.connect() as conn:
        account = conn.execute(select(accounts).where(accounts.c.user_id == user, accounts.c.kind == kind)).mappings().first()
        if not account: return {'kind': kind, 'cash': None, 'positions': [], 'orders': [], 'cost_basis': '0.00', 'realized': '0.00', 'market_value': None}
        ps = conn.execute(select(positions).where(positions.c.account_id == account['id'], positions.c.quantity > 0)).mappings().all()
        os = conn.execute(select(orders).where(orders.c.account_id == account['id']).order_by(orders.c.created.desc())).mappings().all()
        return {'kind': kind, 'cash': money(account['cash']) if kind == 'paper' else None,
                'cost_basis': money(sum(p['cost'] for p in ps)), 'realized': money(sum(o['realized'] for o in os)), 'market_value': None,
                'positions': [{'symbol': p['symbol'], 'quantity': p['quantity'], 'cost': money(p['cost']),
                               'average_cost': f"{Decimal(p['cost']) / p['quantity'] / 100:.4f}"} for p in ps],
                'orders': [present_order(o) for o in os]}
