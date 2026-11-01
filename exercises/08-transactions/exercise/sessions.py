"""Repete, com duas ligações (sessão A e sessão B), as sequências do README:
lost update, as duas correções e o deadlock.

    uv run python sessions.py
"""

import threading
import time

import psycopg

from db import connect


def show(who, sql, conn):
    cur = conn.execute(sql)
    result = cur.fetchone() if cur.description else cur.statusmessage
    print(f"  {who}: {sql:<75} -> {result}")


def reset():
    with connect(autocommit=True) as c:
        c.execute("UPDATE customer SET balance = 100 WHERE customer_id IN (1, 2)")


def balance():
    with connect() as c:
        return c.execute("SELECT balance FROM customer WHERE customer_id = 1").fetchone()[0]


def lost_update():
    print("\n1. LOST UPDATE (cada sessão quer tirar 10)")
    reset()
    a, b = connect(autocommit=True), connect(autocommit=True)  # como no psql: BEGIN e COMMIT à mão
    show("A", "BEGIN", a)
    show("A", "SELECT balance FROM customer WHERE customer_id = 1", a)
    show("B", "BEGIN", b)
    show("B", "SELECT balance FROM customer WHERE customer_id = 1", b)
    show("A", "UPDATE customer SET balance = 90 WHERE customer_id = 1", a)
    show("A", "COMMIT", a)
    show("B", "UPDATE customer SET balance = 90 WHERE customer_id = 1", b)
    show("B", "COMMIT", b)
    print(f"  saldo final = {balance()} (devia ser 80)")


def fix_atomic():
    print("\n2a. CORREÇÃO: UPDATE atómico")
    reset()
    a, b = connect(autocommit=True), connect(autocommit=True)  # como no psql: BEGIN e COMMIT à mão
    sql = "UPDATE customer SET balance = balance - 10 WHERE customer_id = 1 AND balance >= 10"
    show("A", "BEGIN", a)
    show("B", "BEGIN", b)
    show("A", sql, a)
    # B fica à espera do lock de A; corre numa thread para A poder fazer COMMIT
    t = threading.Thread(target=lambda: (show("B", sql, b), show("B", "COMMIT", b)))
    t.start()
    time.sleep(0.5)
    print("  B: (à espera que A termine)")
    show("A", "COMMIT", a)
    t.join()
    print(f"  saldo final = {balance()} (certo)")


def fix_for_update():
    print("\n2b. CORREÇÃO: SELECT ... FOR UPDATE")
    reset()
    a, b = connect(autocommit=True), connect(autocommit=True)  # como no psql: BEGIN e COMMIT à mão
    show("A", "BEGIN", a)
    show("A", "SELECT balance FROM customer WHERE customer_id = 1 FOR UPDATE", a)

    def session_b():
        show("B", "BEGIN", b)
        cur = b.execute("SELECT balance FROM customer WHERE customer_id = 1 FOR UPDATE")
        value = cur.fetchone()[0]
        print(f"  B: SELECT balance FROM customer WHERE customer_id = 1 FOR UPDATE{'':<13} -> ({value},)  (só depois do COMMIT de A)")
        show("B", f"UPDATE customer SET balance = {value - 10} WHERE customer_id = 1", b)
        show("B", "COMMIT", b)

    t = threading.Thread(target=session_b)
    t.start()
    time.sleep(0.5)
    show("A", "UPDATE customer SET balance = 90 WHERE customer_id = 1", a)
    show("A", "COMMIT", a)
    t.join()
    print(f"  saldo final = {balance()} (certo)")


def deadlock():
    print("\n3. DEADLOCK")
    reset()
    a, b = connect(autocommit=True), connect(autocommit=True)  # como no psql: BEGIN e COMMIT à mão
    show("A", "BEGIN", a)
    show("B", "BEGIN", b)
    show("A", "UPDATE customer SET balance = balance - 10 WHERE customer_id = 1", a)
    show("B", "UPDATE customer SET balance = balance - 10 WHERE customer_id = 2", b)

    def session_a():
        try:
            show("A", "UPDATE customer SET balance = balance - 10 WHERE customer_id = 2", a)
            show("A", "COMMIT", a)
        except psycopg.Error as e:
            print(f"  A: ERROR: {e}")
            a.execute("ROLLBACK")

    t = threading.Thread(target=session_a)
    t.start()  # A fica à espera da linha 2 (que B tem)
    time.sleep(0.5)
    try:
        # B pede a linha 1 (que A tem): cada um espera pelo outro
        show("B", "UPDATE customer SET balance = balance - 10 WHERE customer_id = 1", b)
        show("B", "COMMIT", b)
    except psycopg.Error as e:
        print(f"  B: ERROR: {e}")
        b.execute("ROLLBACK")
    t.join()


lost_update()
fix_atomic()
fix_for_update()
deadlock()
