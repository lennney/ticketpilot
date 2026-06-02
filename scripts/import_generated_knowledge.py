#!/usr/bin/env python3
"""
把 cross_border_generated.json 的 36 条结构化知识入库到 knowledge_chunks 表。
"""
import json
import os
import hashlib
import uuid

import psycopg
from dotenv import load_dotenv

load_dotenv('.env.local')

def get_conn():
    return psycopg.connect(
        host=os.environ['DB_HOST'],
        port=int(os.environ.get('DB_PORT', 5432)),
        dbname=os.environ['DB_NAME'],
        user=os.environ['DB_USER'],
        password=os.environ['DB_PASSWORD']
    )

def generate_fake_embedding(text, dim=512):
    """Generate deterministic fake embedding for testing."""
    import random
    random.seed(hashlib.sha256(text.encode()).hexdigest())
    return [random.uniform(-1, 1) for _ in range(dim)]

def insert_knowledge(conn, knowledge):
    """Insert a knowledge chunk into the database."""
    with conn.cursor() as cur:
        doc_id = str(uuid.uuid4())
        parent_id = str(uuid.uuid4())
        child_id = str(uuid.uuid4())
        
        # Normalize type to uppercase
        doc_type = knowledge['type'].upper()
        
        # Handle different formats (CASE has issue_summary+resolution, FAQ/POLICY has title+content)
        if doc_type == 'CASE':
            title = knowledge.get('issue_summary', knowledge.get('case_id', ''))
            content = knowledge.get('resolution', '')
        else:
            title = knowledge.get('title', '')
            content = knowledge.get('content', '')
        
        # Parent chunk (title + summary)
        parent_content = f"{title}\n\n{content[:100]}..."
        parent_hash = hashlib.sha256(parent_content.encode()).hexdigest()
        parent_embedding = generate_fake_embedding(parent_content)
        
        # Child chunk (full content)
        child_content = content
        child_hash = hashlib.sha256(child_content.encode()).hexdigest()
        child_embedding = generate_fake_embedding(child_content)
        
        # Insert parent
        cur.execute("""
            INSERT INTO knowledge_chunks 
            (id, doc_id, doc_type, parent_chunk_id, chunk_level, business_domain, 
             content, content_hash, embedding, source_table)
            VALUES (%s, %s, %s, NULL, 1, %s, %s, %s, %s::vector, 'generated')
        """, (parent_id, doc_id, doc_type, knowledge['domain'],
              parent_content, parent_hash, str(parent_embedding)))
        
        # Insert child
        cur.execute("""
            INSERT INTO knowledge_chunks 
            (id, doc_id, doc_type, parent_chunk_id, chunk_level, business_domain, 
             content, content_hash, embedding, source_table)
            VALUES (%s, %s, %s, %s, 2, %s, %s, %s, %s::vector, 'generated')
        """, (child_id, doc_id, doc_type, parent_id, knowledge['domain'],
              child_content, child_hash, str(child_embedding)))
        
        conn.commit()
        return parent_id, child_id

def main():
    print("=== 导入 cross_border_generated.json ===")
    
    # Load data
    with open('data/knowledge/external/cross_border_generated.json') as f:
        data = json.load(f)
    
    print(f"加载 {len(data)} 条知识")
    
    # Connect to DB
    conn = get_conn()
    
    # Check existing
    with conn.cursor() as cur:
        cur.execute("SELECT COUNT(*) FROM knowledge_chunks")
        existing_before = cur.fetchone()[0]
        print(f"入库前: {existing_before} chunks")
    
    # Insert each item
    inserted = 0
    failed = 0
    
    for i, item in enumerate(data):
        try:
            parent_id, child_id = insert_knowledge(conn, item)
            title_display = item.get('title', item.get('issue_summary', item.get('content',''))[:30])
            print(f"  [{i+1:2d}/{len(data)}] ✓ {item['type']:6s} | {title_display[:40]}")
            inserted += 1
        except Exception as e:
            print(f"  [{i+1:2d}/{len(data)}] ✗ {item.get('type','?'):6s} | {item.get('title', item.get('content','')[:30])[:40]} | Error: {e}")
            conn.rollback()
            failed += 1
    
    # Final count
    with conn.cursor() as cur:
        cur.execute("SELECT COUNT(*) FROM knowledge_chunks")
        total = cur.fetchone()[0]
        cur.execute("SELECT chunk_level, doc_type, COUNT(*) FROM knowledge_chunks GROUP BY chunk_level, doc_type ORDER BY chunk_level, doc_type")
        breakdown = cur.fetchall()
    
    conn.close()
    
    print(f"\n=== 完成 ===")
    print(f"入库前: {existing_before} chunks")
    print(f"新入库: {inserted} 条知识 ({inserted * 2} chunks)")
    print(f"失败: {failed} 条")
    print(f"入库后: {total} chunks")
    print(f"明细:")
    for r in breakdown:
        print(f"  L{r[0]} {r[1]}: {r[2]}")

if __name__ == '__main__':
    main()
