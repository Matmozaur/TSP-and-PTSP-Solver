import os
import sqlite3
from io import BytesIO
from TSP_PTSP_solver.settings import BASE_DIR, STATIC_ROOT


def save_tsp(graph, solution, name, description):
    graph = str(graph)
    solution = str(solution)
    conn = sqlite3.connect(os.path.join(BASE_DIR, 'db.sqlite3'))
    cur = conn.cursor()
    cur.execute('INSERT INTO TSP (Graph, Solution, Name, Description) VALUES (?, ?, ?, ?);', (graph, solution, name, description))
    cur.execute('select last_insert_rowid();')
    id = cur.fetchall()
    conn.commit()
    conn.close()


def load_all_tsp():
    conn = sqlite3.connect(os.path.join(BASE_DIR, 'db.sqlite3'))
    cur = conn.cursor()
    cur.execute('select Name, Description from TSP ')
    data = cur.fetchall()
    conn.close()
    return data


def load_tsp_sol(name):
    conn = sqlite3.connect(os.path.join(BASE_DIR, 'db.sqlite3'))
    cur = conn.cursor()
    all_info = {}
    cur.execute('select Graph, Solution, Name, Description from TSP where name=?', (name,))
    data = cur.fetchall()
    all_info['graph'] = data[0][0]
    all_info['solution'] = data[0][1]
    all_info['name'] = data[0][2]
    all_info['description'] = data[0][3]
    conn.close()
    return all_info

