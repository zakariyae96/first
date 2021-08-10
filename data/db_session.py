from py2neo import Graph


def db_auth():
    user = 'neo4j'
    #pword = 'Neo4j'
    mdp = open("mdp.txt", "r").read()
    graph = Graph("localhost:7474", user=user, password=mdp)
    return graph
