# Neo4j NVL — Best Practices

## What is NVL

Neo4j Visualization Library (NVL) is a React component library for rendering interactive graph visualizations. It expects data in a specific format: an object with a `nodes` array and a `relationships` array, each element having mandatory attributes.

---

## Cypher Query Format

### Avoid: returning a `path` object

```cypher
MATCH path = (n)-[r]-(p)
RETURN path
```

This returns a single opaque `path` object. All the transformation work to extract nodes and relationships into the format NVL expects has to be done in JavaScript — which is verbose and error-prone.

### Avoid: returning raw node and relationship variables

```cypher
MATCH (n:Label1)-[r:REL]-(p:Label2)
RETURN n, r, p
```

Better — results are separated into distinct variables — but NVL still expects a specific shape (`nodes` / `relationships` with specific attributes), so JavaScript transformation is still required.

### Recommended: shape the output directly in Cypher

Let Cypher do the transformation. Return exactly the structure NVL expects, so the JavaScript layer receives ready-to-use data with zero additional mapping.

```cypher
MATCH (n1:Label1)-[rel:REL]-(n2:Label2)
RETURN {
  nodes: [
    {
      id: elementId(n1),
      labels: labels(n1),
      properties: properties(n1)
    },
    {
      id: elementId(n2),
      labels: labels(n2),
      properties: properties(n2)
    }
  ],
  relationships: [
    {
      id: elementId(rel),
      from: elementId(n1),
      to: elementId(n2),
      type: type(rel),
      properties: properties(rel)
    }
  ]
} AS graph
```

This result maps directly to NVL's expected input — no JavaScript transformation needed.

---

## Node and Relationship IDs

### Use `elementId()`, not `id()`

Neo4j previously exposed internal integer IDs via the `id()` function. This has been superseded by `elementId()`, which returns a string unique identifier. The change was made to avoid confusion with user-defined `id` properties on nodes.

- Use `elementId(n)` to retrieve the unique identifier of a node or relationship.
- Store it in the `id` field, which is the attribute name NVL expects.

```cypher
id: elementId(n1)   -- correct
id: id(n1)          -- deprecated, avoid
```

---

## Summary

| Practice | Recommendation |
|---|---|
| Query return format | Return a shaped object with `nodes` and `relationships` directly from Cypher |
| Node/relationship identifier | Use `elementId()`, stored as `id` |
| JavaScript transformation | Keep it minimal — offload shaping to Cypher |
