from neo4j import GraphDatabase, basic_auth

NEO4J_URI  = "neo4j://<IP>:7687"
NEO4J_USER = "neo4j"
NEO4J_PASS = "<PASSWORD>"


with GraphDatabase.driver(NEO4J_URI, auth=basic_auth(NEO4J_USER, NEO4J_PASS)) as driver:
    driver.verify_connectivity()
    with driver.session() as s:
        print("Current user:", s.run("SHOW CURRENT USER").single())