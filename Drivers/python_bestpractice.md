# Best Practices — Neo4j Python Driver

The best practices below are a corpus collected from many sources :
- https://medium.com/neo4j/querying-neo4j-clusters-7d6fde75b5b4
- https://neo4j.com/docs/python-manual/current/performance/ 
- https://support.neo4j.com/s/article/14249408309395-Neo4j-Driver-Best-Practices
- https://neo4j.com/blog/developer/neo4j-driver-best-practices/
- https://support.neo4j.com/s/article/1500004773941-How-to-operate-with-many-applications-connecting-to-my-Aura-Instance-using-the-driver-maximum-connections
- https://neo4j.com/developer/kb/protecting-against-cypher-injection/
- https://neo4j.com/docs/operations-manual/current/database-administration/routing-decisions/#_illustrated_routing_decision_tree
- https://deepwiki.com/neo4j/neo4j-python-driver/1-overview
- https://neo4j.com/docs/bolt/current/driver-api/#client-side-routing

## 1. Use the Rust Extension

The Rust extension to the Python driver is an alternative driver package that yields a 3x to 10x speedup compared to the regular driver. You can install it with `pip install neo4j-rust-ext`, either alongside the `neo4j` package or as a replacement to it. Usage-wise, the drivers are identical: everything in this guide applies to both packages.

```bash
pip install neo4j-rust-ext
```

## 2. Driver Management

Driver objects in Neo4j contain connection pools which can be typically expensive to create, it may take up to a few seconds to create all of the necessary connections and establish connectivity. Best practice here should be to only create one driver instance per Neo4j DBMS, hold on to that and use it for everything.

This is important in environments when using serverless cloud functions, such as AWS Lambda, where if you created a driver instance every time your code runs, it will incur a performance penalty. You may also want to consider changing connectivity settings to reduce the number of connections created, in order to reduce cold startup time.

Drivers are generally heavyweight objects that expect to be reused many times, whilst Sessions on the other hand are cheap, you can create and close as many of them as you like. You should create a session to run a transaction and close it after it has been used. They should be considered disposable.


```python
from neo4j import GraphDatabase

driver = GraphDatabase.driver("bolt://localhost:7687", auth=("neo4j", "password"))

# On application shutdown
driver.close()
```

Or use a context manager:

```python
with GraphDatabase.driver("bolt://localhost:7687", auth=("neo4j", "password")) as driver:
    ...
```

## 3. Connectivity Check

Normally, the Neo4j driver creates connections as needed and manages them in a pool; by verifying connectivity at the very beginning, it forces the driver to create a connection at that moment. If the address, username, or password is wrong, it will fail immediately. It can be helpful to validate connectivity before starting to run any Cypher queries, especially as if you did receive any errors in your queries, you have already ruled out it being the result of a connection error.

```python
driver.verify_connectivity()
```

## 4. Session Management

Do **not** reuse a session — create a new session per logical unit of work:

```python
with driver.session(database="neo4j") as session:
    result = session.run("MATCH (n) RETURN n LIMIT 10")
```

Always specify the database name (`database=`) to avoid depending on the server default.

## 5. Specify the Database Name

Specify the target database on all queries, either with the database_ parameter in Driver.execute_query() or with the database parameter when creating new sessions. If no database is provided, the driver has to send an extra request to the server to figure out what the default database is. The overhead is minimal for a single query, but becomes significant over hundreds of queries.

```python
with driver.session(database="neo4j") as session:
    ...
```

## 6. Explicit vs. Implicit Transactions

Prefer **managed transactions** (`execute_read` / `execute_write`) over auto-commit transactions to benefit from automatic retries:

```python
def get_user(tx, user_id):
    result = tx.run("MATCH (u:User {id: $id}) RETURN u", id=user_id)
    return result.single()

with driver.session() as session:
    user = session.execute_read(get_user, user_id=42)
```

`execute_read` / `execute_write` (formerly `read_transaction` / `write_transaction`) automatically handle retries on transient errors.

## 8. Always Use Parameters (Never f-strings)

**Avoid:**

```python
tx.run(f"MATCH (u:User {{name: '{name}'}}) RETURN u")  # Cypher injection!
```

**Do:**

```python
tx.run("MATCH (u:User {name: $name}) RETURN u", name=name)
```

## 9. Consume Results Inside the Transaction

`Result` objects are only valid for the duration of the transaction. Materialize the data before exiting:

```python
def get_names(tx):
    result = tx.run("MATCH (u:User) RETURN u.name AS name")
    return [record["name"] for record in result]  # consumed inside the tx
```

## 10. Routing and Causal Consistency

For a Neo4j cluster, use `neo4j://` (instead of `bolt://`) to enable automatic routing:

```python
driver = GraphDatabase.driver("neo4j://localhost:7687", auth=("neo4j", "password"))
```

Use bookmarks if you need causal consistency across sessions:

```python
with driver.session() as session:
    session.execute_write(create_user, ...)
    bookmark = session.last_bookmarks()

with driver.session(bookmarks=bookmark) as session:
    session.execute_read(read_user, ...)
```

## 11. Error Handling

Catch Neo4j-specific exceptions:

```python
from neo4j.exceptions import ServiceUnavailable, ClientError, TransientError

try:
    with driver.session() as session:
        session.execute_write(my_tx_func)
except TransientError as e:
    print(f"Transient error (retry possible): {e}")
except ClientError as e:
    print(f"Cypher or constraint error: {e}")
except ServiceUnavailable:
    print("Neo4j database unreachable")
```

## 12. Connection Pool

Configure the pool according to your workload:

```python
driver = GraphDatabase.driver(
    "neo4j://localhost:7687",
    auth=("neo4j", "password"),
    max_connection_pool_size=50,        # default: 100
    connection_acquisition_timeout=30,  # seconds
    connection_timeout=5,
)
```

## 13. Logging & Monitoring

Enable logs for debugging:

```python
import logging
logging.getLogger("neo4j").setLevel(logging.DEBUG)
```

## 14. Async (for FastAPI, asyncio, etc.)

Use the dedicated async driver:

```python
from neo4j import AsyncGraphDatabase

async def main():
    async with AsyncGraphDatabase.driver("neo4j://localhost:7687", auth=("neo4j", "password")) as driver:
        async with driver.session() as session:
            result = await session.run("MATCH (n) RETURN n LIMIT 5")
            records = await result.values()
```