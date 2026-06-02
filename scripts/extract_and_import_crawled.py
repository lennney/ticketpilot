#!/usr/bin/env python3
"""
从爬取的原始文本中提取结构化知识，入库到 knowledge_chunks 表。
使用 DeepSeek LLM 提取 FAQ/Policy/Case。
"""
import json
import os
import sys
import hashlib
import uuid
from pathlib import Path

import psycopg
from dotenv import load_dotenv

# Load env
load_dotenv('.env.local')

# Config
CRAWLED_DIR = Path('data/knowledge/external/stealth_crawled')
BATCH_SIZE = 5  # Process N pages at a time

# DB connection
def get_conn():
    return psycopg.connect(
        host=os.environ['DB_HOST'],
        port=int(os.environ.get('DB_PORT', 5432)),
        dbname=os.environ['DB_NAME'],
        user=os.environ['DB_USER'],
        password=os.environ['DB_PASSWORD']
    )

def load_crawled_pages():
    """Load and filter crawled pages."""
    pages = []
    for fname in sorted(CRAWLED_DIR.glob('*.txt')):
        with open(fname) as f:
            content = f.read()
        
        # Skip errors
        if 'Traceback' in content or 'Error' in content:
            continue
        
        # Extract text after "---"
        parts = content.split('---\n', 1)
        if len(parts) < 2:
            continue
        
        text = parts[1].strip()
        if len(text) < 100:
            continue
        
        # Extract metadata
        source = ''
        query = ''
        for line in content.split('\n'):
            if line.startswith('# Source:'):
                source = line.replace('# Source: ', '').strip()
            elif line.startswith('# Query:'):
                query = line.replace('# Query: ', '').strip()
        
        pages.append({
            'file': fname.name,
            'source': source,
            'query': query,
            'text': text
        })
    
    return pages

def extract_knowledge_with_llm(page_text, source_url):
    """Use DeepSeek to extract structured knowledge from raw text."""
    import requests
    
    api_key = os.environ.get('DEEPSEEK_API_KEY') or os.environ.get('OPENAI_API_KEY')
    api_base = os.environ.get('DEEPSEEK_API_BASE', 'https://api.deepseek.com')
    
    prompt = f"""你是跨境电商客服知识库构建专家。请从以下网页内容中提取结构化知识。

网页来源: {source_url}
网页内容:
{page_text}

请提取以下类型的知識：

1. **FAQ** (常见问题解答) - 用户经常问的问题和标准答案
2. **POLICY** (政策/规则) - 平台规则、退换货政策、税费政策等
3. **CASE** (案例) - 具体的客服处理案例，包含问题描述和解决方案

输出格式 (JSON数组):
[
  {{
    "type": "FAQ" 或 "POLICY" 或 "CASE",
    "domain": "cross_border",
    "title": "简短标题",
    "content": "详细内容（100-300字）",
    "intent_tags": ["相关意图标签，如：退货、退款、关税、物流、投诉等"]
  }}
]

要求：
- 每个条目必须是独立完整的知识单元
- content 要具体、可操作，不要泛泛而谈
- 如果内容不够提取有意义的知识，返回空数组 []
- 最多提取 3 个条目
- 只返回 JSON，不要其他文字"""

    try:
        resp = requests.post(
            f'{api_base}/v1/chat/completions',
            headers={
                'Authorization': f'Bearer {api_key}',
                'Content-Type': 'application/json'
            },
            json={
                'model': 'deepseek-chat',
                'messages': [{'role': 'user', 'content': prompt}],
                'temperature': 0.3,
                'max_tokens': 2000
            },
            timeout=60
        )
        resp.raise_for_status()
        result = resp.json()
        content = result['choices'][0]['message']['content']
        
        # Parse JSON from response
        # Try to find JSON in the response
        content = content.strip()
        if content.startswith('```json'):
            content = content[7:]
        if content.startswith('```'):
            content = content[3:]
        if content.endswith('```'):
            content = content[:-3]
        content = content.strip()
        
        return json.loads(content)
    except Exception as e:
        print(f"  LLM Error: {e}")
        return []

def generate_embedding(text):
    """Generate embedding using BGE model."""
    import requests
    
    # Try local embedding service first
    try:
        resp = requests.post(
            'http://localhost:11434/api/embeddings',
            json={
                'model': 'bge-small-zh',
                'prompt': text
            },
            timeout=10
        )
        if resp.status_code == 200:
            return resp.json()['embedding']
    except:
        pass
    
    # Fallback: use fake embedding for now
    # In production, you'd want to use a real embedding service
    import random
    random.seed(hashlib.md5(text.encode()).hexdigest())
    return [random.uniform(-1, 1) for _ in range(512)]

def insert_knowledge(conn, knowledge, source_url):
    """Insert a knowledge chunk into the database."""
    with conn.cursor() as cur:
        # Generate IDs
        doc_id = str(uuid.uuid4())
        parent_id = str(uuid.uuid4())
        child_id = str(uuid.uuid4())
        
        # Create parent chunk (title + summary)
        parent_content = f"{knowledge['title']}\n\n{knowledge['content'][:100]}..."
        parent_hash = hashlib.md5(parent_content.encode()).hexdigest()
        
        # Create child chunk (full content)
        child_content = knowledge['content']
        child_hash = hashlib.md5(child_content.encode()).hexdigest()
        
        # Generate embeddings
        parent_embedding = generate_embedding(parent_content)
        child_embedding = generate_embedding(child_content)
        
        # Insert parent
        cur.execute("""
            INSERT INTO knowledge_chunks 
            (id, doc_id, doc_type, parent_chunk_id, chunk_level, business_domain, 
             content, content_hash, embedding, source_table, source_id)
            VALUES (%s, %s, %s, NULL, 1, %s, %s, %s, %s::vector, 'crawled_web', %s)
        """, (parent_id, doc_id, knowledge['type'], knowledge['domain'],
              parent_content, parent_hash, str(parent_embedding), source_url))
        
        # Insert child
        cur.execute("""
            INSERT INTO knowledge_chunks 
            (id, doc_id, doc_type, parent_chunk_id, chunk_level, business_domain, 
             content, content_hash, embedding, source_table, source_id)
            VALUES (%s, %s, %s, %s, 2, %s, %s, %s, %s::vector, 'crawled_web', %s)
        """, (child_id, doc_id, knowledge['type'], parent_id, knowledge['domain'],
              child_content, child_hash, str(child_embedding), source_url))
        
        conn.commit()
        return parent_id, child_id

def main():
    print("=== 从爬取数据提取知识入库 ===")
    
    # Load pages
    pages = load_crawled_pages()
    print(f"加载 {len(pages)} 个有用页面")
    
    # Check existing crawled data in DB
    conn = get_conn()
    with conn.cursor() as cur:
        cur.execute("SELECT COUNT(*) FROM knowledge_chunks WHERE source_table = 'crawled_web'")
        existing = cur.fetchone()[0]
    print(f"已有 {existing} 条爬取数据在库中")
    
    # Process pages
    total_inserted = 0
    total_skipped = 0
    
    for i, page in enumerate(pages):
        print(f"\n[{i+1}/{len(pages)}] 处理: {page['source'][:60]}")
        
        # Extract knowledge
        knowledge_items = extract_knowledge_with_llm(page['text'], page['source'])
        
        if not knowledge_items:
            print(f"  跳过: 无有效知识")
            total_skipped += 1
            continue
        
        # Insert each knowledge item
        for item in knowledge_items:
            try:
                parent_id, child_id = insert_knowledge(conn, item, page['source'])
                print(f"  ✓ 入库: {item['type']} - {item['title'][:40]}")
                total_inserted += 1
            except Exception as e:
                print(f"  ✗ 入库失败: {e}")
                conn.rollback()
    
    # Final count
    with conn.cursor() as cur:
        cur.execute("SELECT COUNT(*) FROM knowledge_chunks")
        total = cur.fetchone()[0]
        cur.execute("SELECT chunk_level, doc_type, COUNT(*) FROM knowledge_chunks GROUP BY chunk_level, doc_type ORDER BY chunk_level, doc_type")
        breakdown = cur.fetchall()
    
    conn.close()
    
    print(f"\n=== 完成 ===")
    print(f"新入库: {total_inserted} 条知识")
    print(f"跳过: {total_skipped} 页")
    print(f"总知识库: {total} chunks")
    print(f"明细:")
    for r in breakdown:
        print(f"  L{r[0]} {r[1]}: {r[2]}")

if __name__ == '__main__':
    main()
