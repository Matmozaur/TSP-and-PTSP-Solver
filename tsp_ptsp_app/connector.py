import os
import sqlite3
from io import BytesIO
from TSP_PTSP_solver.settings import BASE_DIR, STATIC_ROOT


def save_tsp(graph, solution, name, description):
    print(name)
    graph = str(graph)
    solution = str(solution)
    conn = sqlite3.connect(os.path.join(BASE_DIR, 'db.sqlite3'))
    cur = conn.cursor()
    cur.execute('INSERT INTO TSP (Graph, Solution, Name, Description) VALUES (?, ?, ?, ?);', (graph, solution, name, description))
    cur.execute('select last_insert_rowid();')
    id = cur.fetchall()
    conn.commit()
    conn.close()


# save_tsp('''{
#     "type": "adjacency matrix",
#     "graph": {
#         "names": null,
# 		"matrix": [
#           [0,20,3,4,5],
#           [10,0,3,40,5],
#           [1,2,0,4,50],
#           [10,2,30,0,5],
#           [1,2,3,2,0]]
#         }
#     }''', '[0,1,2,3,4]', 'Test', 'testing')
