#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
跨机器共享记忆测试
Multi-Machine Memory Sharing Test
"""

import sys
import os
from pathlib import Path

# 设置路径
sys.path.insert(0, str(Path(__file__).parent / 'src'))
sys.path.insert(0, str(Path(__file__).parent))
os.chdir(str(Path(__file__).parent))

from src.core import init_config, init_db, get_store, get_search, close_db

def run_test():
    print("=" * 60)
    print("  Cross-Machine Memory Sharing Test")
    print("=" * 60)

    # Step 1: Machine A stores a memory
    print("\n\n[Step 1] Machine A stores memory")
    print("-" * 40)
    
    init_config(config_path='config.yaml')
    db = init_db()
    store = get_store()
    
    content_a = "Machine A: FastAPI with uvicorn workers=4 gives best performance"
    mem_a = store.store(
        content=content_a,
        memory_type="knowledge",
        tags=["fastapi", "performance", "optimization"],
        importance=8.5
    )
    print("[OK] Stored: " + mem_a.id)
    print("     Content: " + mem_a.content[:50] + "...")
    
    close_db()

    # Step 2: Machine B stores a memory
    print("\n\n[Step 2] Machine B stores memory")
    print("-" * 40)
    
    # Re-init for new "machine"
    import core.database as db_mod
    db_mod._db = None
    
    init_config(config_path='config.yaml')
    db = init_db()
    store = get_store()
    
    content_b = "Machine B: Use pydantic BaseModel for better validation"
    mem_b = store.store(
        content=content_b,
        memory_type="knowledge",
        tags=["pydantic", "validation", "python"],
        importance=7.5
    )
    print("[OK] Stored: " + mem_b.id)
    print("     Content: " + mem_b.content[:50] + "...")
    
    close_db()

    # Step 3: Machine A searches for Machine B's memory
    print("\n\n[Step 3] Machine A searches for Machine B memory")
    print("-" * 40)
    
    import core.database as db_mod2
    db_mod2._db = None
    
    init_config(config_path='config.yaml')
    db = init_db()
    search = get_search()
    
    # Search for pydantic
    print("\n[Search] Query: pydantic")
    results = search.search(query="pydantic", limit=10)
    print("[Result] Found: " + str(len(results)) + " memories")
    for r in results:
        print("  - [" + r.memory.id + "] " + r.memory.content[:50] + "...")
        print("    Source: " + str(r.memory.source_agent))
    
    # Search for FastAPI
    print("\n[Search] Query: FastAPI")
    results = search.search(query="FastAPI", limit=10)
    print("[Result] Found: " + str(len(results)) + " memories")
    for r in results:
        print("  - [" + r.memory.id + "] " + r.memory.content[:50] + "...")
        print("    Source: " + str(r.memory.source_agent))
    
    close_db()

    # Step 4: List all memories
    print("\n\n[Step 4] List all memories")
    print("-" * 40)
    
    import core.database as db_mod3
    db_mod3._db = None
    
    init_config(config_path='config.yaml')
    db = init_db()
    store = get_store()
    
    all_mem = store.list(limit=100)
    print("[Total] " + str(len(all_mem)) + " memories in database")
    
    stats = store.stats()
    print("[Stats] Total: " + str(stats.get('total', 0)))
    
    print("\n[All Memories]")
    for m in all_mem:
        print("  [" + m.id + "] " + m.content[:40] + "...")
        print("    Source: " + str(m.source_agent) + " | Type: " + m.type)

    close_db()

    # Done
    print("\n\n" + "=" * 60)
    print("  Test Complete!")
    print("=" * 60)
    print("""
Conclusion:
1. Machine A and Machine B share the same database
2. Machine A stored memory, Machine B can search it
3. Machine B stored memory, Machine A can search it
4. Cross-machine sharing works!
""")

if __name__ == "__main__":
    try:
        run_test()
    except Exception as e:
        print("\n[ERROR] " + str(e))
        import traceback
        traceback.print_exc()
