from neo4j import GraphDatabase

passwords = ["password123", "your_password", "password"]
driver = None
for p in passwords:
    try:
        d = GraphDatabase.driver("bolt://localhost:7687", auth=("neo4j", p))
        d.verify_connectivity()
        driver = d
        break
    except Exception:
        pass

if not driver:
    print("Could not connect")
    exit(1)

with driver.session() as s:
    res1 = s.run("MATCH (c1:Course)-[r:REQUIRES]->(c2:Course) RETURN c1.name as c1, r.raw_text, c2.name as c2, c1.department as d1, c2.department as d2 LIMIT 150")
    print("\n=== MAPPED REQUIRES ===")
    count = 0
    for r in res1:
        print(f"[{r['c1']} ({r.get('d1','')})] -[REQUIRES: '{r['r.raw_text']}']-> [{r['c2']} ({r.get('d2','')})]")
        count += 1
    print(f"Total mapped: {count}")
    
    res2 = s.run("MATCH (c:Course) WHERE c.unmapped_prerequisites IS NOT NULL AND c.unmapped_prerequisites <> '' RETURN c.name, c.department, c.unmapped_prerequisites ORDER BY c.name")
    unmapped = list(res2)
    print(f"\n=== UNMAPPED (Total: {len(unmapped)}) ===")
    import random
    samples = random.sample(unmapped, min(20, len(unmapped)))
    for r in samples:
        print(f"[{r['c.name']}]: {r['c.unmapped_prerequisites']}")

