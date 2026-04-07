import sys
import os
from pathlib import Path

script_dir = Path(__file__).parent
log_file = script_dir / "test_output.txt"

src_dir = script_dir / "src"

with open(log_file, 'w') as f:
    f.write("=" * 60 + "\n")
    f.write("Multi-Machine Memory Sharing Test\n")
    f.write("=" * 60 + "\n\n")
    f.flush()
    
    try:
        # Setup path
        sys.path.insert(0, str(src_dir))
        sys.path.insert(0, str(script_dir))
        os.chdir(str(script_dir))
        
        import core.database as db_mod
        db_mod._db = None
        
        from src.core import init_config, init_db, get_store, get_search, close_db
        
        f.write("[Step 1] Machine A stores memory\n")
        f.flush()
        
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
        f.write("[OK] Stored: " + mem_a.id + "\n")
        f.write("     Content: " + content_a[:50] + "...\n")
        f.flush()
        
        close_db()
        
        f.write("\n[Step 2] Machine B stores memory\n")
        f.flush()
        
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
        f.write("[OK] Stored: " + mem_b.id + "\n")
        f.write("     Content: " + content_b[:50] + "...\n")
        f.flush()
        
        close_db()
        
        f.write("\n[Step 3] Machine A searches for Machine B memory\n")
        f.flush()
        
        db_mod._db = None
        init_config(config_path='config.yaml')
        db = init_db()
        search = get_search()
        
        f.write("\n[Search] Query: pydantic\n")
        f.flush()
        results = search.search(query="pydantic", limit=10)
        f.write("[Result] Found: " + str(len(results)) + " memories\n")
        f.flush()
        
        for r in results:
            f.write("  - [" + r.memory.id + "] " + r.memory.content[:50] + "...\n")
            f.write("    Source: " + str(r.memory.source_agent) + "\n")
            f.flush()
            
            try:
                d = r.to_dict()
                f.write("    to_dict: OK\n")
                f.flush()
                
                import json
                json_str = json.dumps(d)
                f.write("    JSON: OK\n")
                f.flush()
            except Exception as e:
                f.write("    ERROR in to_dict/JSON: " + str(e) + "\n")
                import traceback
                traceback.print_exc(file=f)
                f.flush()
        
        close_db()
        
        f.write("\n[Step 4] List all memories\n")
        f.flush()
        
        db_mod._db = None
        init_config(config_path='config.yaml')
        db = init_db()
        store = get_store()
        
        all_mem = store.list(limit=100)
        f.write("[Total] " + str(len(all_mem)) + " memories\n")
        f.flush()
        
        stats = store.stats()
        f.write("[Stats] Total: " + str(stats.get('total', 0)) + "\n")
        f.flush()
        
        f.write("\n[All Memories]\n")
        for m in all_mem:
            f.write("  [" + m.id + "] " + m.content[:40] + "...\n")
            f.write("    Source: " + str(m.source_agent) + " | Type: " + m.type + "\n")
            f.flush()
        
        close_db()
        
        f.write("\n" + "=" * 60 + "\n")
        f.write("Test Complete Successfully!\n")
        f.write("=" * 60 + "\n")
        
    except Exception as e:
        f.write("\n\nERROR: " + str(e) + "\n")
        import traceback
        traceback.print_exc(file=f)
        
print("Check output file:", log_file)
