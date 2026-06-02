#!/usr/bin/env python3
"""
Rebuild embeddings using curl to bypass SSL issues.
"""
import json
import os
import subprocess
import sys
from pathlib import Path

from dotenv import load_dotenv

load_dotenv('.env.local')

API_KEY = os.environ['EMBEDDING_API_KEY']
BASE_URL = os.environ['EMBEDDING_BASE_URL']
MODEL = os.environ['EMBEDDING_MODEL']
DIM = int(os.environ['EMBEDDING_DIM'])

def embed_batch(texts: list[str]) -> list[list[float]]:
    """Embed a batch of texts using curl."""
    data = json.dumps({
        'model': MODEL,
        'input': texts
    })
    
    result = subprocess.run(
        ['curl', '-s', '--max-time', '60',
         '-H', f'Authorization: Bearer {API_KEY}',
         '-H', 'Content-Type: application/json',
         '-d', data,
         f'{BASE_URL}/embeddings'],
        capture_output=True,
        text=True
    )
    
    if result.returncode != 0:
        raise RuntimeError(f'curl failed: {result.stderr}')
    
    response = json.loads(result.stdout)
    if 'error' in response:
        raise RuntimeError(f'API error: {response["error"]}')
    
    # Sort by index
    data_items = sorted(response['data'], key=lambda x: x.get('index', 0))
    return [item['embedding'] for item in data_items]

def main():
    import psycopg
    
    conn = psycopg.connect(
        host=os.environ['DB_HOST'],
        port=int(os.environ.get('DB_PORT', 5432)),
        dbname=os.environ['DB_NAME'],
        user=os.environ['DB_USER'],
        password=os.environ['DB_PASSWORD']
    )
    
    # Get all chunks
    with conn.cursor() as cur:
        cur.execute('SELECT id, content FROM knowledge_chunks ORDER BY id')
        chunks = cur.fetchall()
    
    print(f'找到 {len(chunks)} 个 chunks')
    
    # Process in batches
    batch_size = 10
    for i in range(0, len(chunks), batch_size):
        batch = chunks[i:i+batch_size]
        ids = [str(row[0]) for row in batch]
        texts = [row[1] for row in batch]
        
        try:
            embeddings = embed_batch(texts)
            
            # Update database
            with conn.cursor() as cur:
                for chunk_id, embedding in zip(ids, embeddings):
                    cur.execute(
                        'UPDATE knowledge_chunks SET embedding = %s::vector WHERE id = %s',
                        (str(embedding), chunk_id)
                    )
            conn.commit()
            
            print(f'[{i+1}-{min(i+batch_size, len(chunks))}/{len(chunks)}] ✓')
        except Exception as e:
            print(f'[{i+1}-{min(i+batch_size, len(chunks))}/{len(chunks)}] ✗ {e}')
            conn.rollback()
    
    # Rebuild HNSW index
    print('重建 HNSW 索引...')
    with conn.cursor() as cur:
        cur.execute('DROP INDEX IF EXISTS idx_chunks_embedding_hnsw')
        cur.execute('CREATE INDEX idx_chunks_embedding_hnsw ON knowledge_chunks USING hnsw (embedding vector_cosine_ops)')
    conn.commit()
    
    # Update metadata
    print('更新元数据...')
    with conn.cursor() as cur:
        cur.execute("""
            INSERT INTO embedding_metadata (id, provider, model, dimension, created_at)
            VALUES (1, 'openai_compatible', %s, %s, NOW())
            ON CONFLICT (id) DO UPDATE SET
                provider = EXCLUDED.provider,
                model = EXCLUDED.model,
                dimension = EXCLUDED.dimension,
                created_at = EXCLUDED.created_at
        """, (MODEL, DIM))
    conn.commit()
    
    conn.close()
    print('完成！')

if __name__ == '__main__':
    main()
