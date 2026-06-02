"""
Migration: Add materialized tsvector column for faster FTS.
Run once to set up the column and trigger.
"""
import psycopg
import os
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

def main():
    conn = get_conn()
    conn.autocommit = True
    cur = conn.cursor()
    
    print("=== 添加物化 tsvector 列 ===")
    
    # 1. Add tsvector column
    try:
        cur.execute("""
            ALTER TABLE knowledge_chunks 
            ADD COLUMN IF NOT EXISTS content_tsv tsvector
        """)
        print("✓ 添加 content_tsv 列")
    except Exception as e:
        print(f"  列已存在或错误: {e}")
    
    # 2. Create GIN index on tsvector column
    try:
        cur.execute("""
            CREATE INDEX IF NOT EXISTS idx_chunks_content_tsv 
            ON knowledge_chunks USING gin(content_tsv)
        """)
        print("✓ 创建 GIN 索引 idx_chunks_content_tsv")
    except Exception as e:
        print(f"  索引已存在或错误: {e}")
    
    # 3. Populate existing rows
    cur.execute("""
        UPDATE knowledge_chunks 
        SET content_tsv = to_tsvector('simple', coalesce(content, ''))
        WHERE content_tsv IS NULL
    """)
    print(f"✓ 更新 {cur.rowcount} 行的 content_tsv")
    
    # 4. Create trigger to auto-update on INSERT/UPDATE
    cur.execute("""
        CREATE OR REPLACE FUNCTION knowledge_chunks_tsv_trigger()
        RETURNS trigger AS $$
        BEGIN
            NEW.content_tsv := to_tsvector('simple', coalesce(NEW.content, ''));
            RETURN NEW;
        END
        $$ LANGUAGE plpgsql;
    """)
    print("✓ 创建触发器函数")
    
    cur.execute("""
        DROP TRIGGER IF EXISTS tsvector_update ON knowledge_chunks;
        CREATE TRIGGER tsvector_update
        BEFORE INSERT OR UPDATE ON knowledge_chunks
        FOR EACH ROW EXECUTE FUNCTION knowledge_chunks_tsv_trigger();
    """)
    print("✓ 创建触发器 tsvector_update")
    
    # 5. Verify
    cur.execute("SELECT COUNT(*) FROM knowledge_chunks WHERE content_tsv IS NOT NULL")
    count = cur.fetchone()[0]
    print(f"\n验证: {count} 行有 content_tsv")
    
    # 6. Test query performance
    import time
    
    # Old way (compute on-the-fly)
    start = time.time()
    cur.execute("""
        SELECT id FROM knowledge_chunks 
        WHERE to_tsvector('simple', content) @@ to_tsquery('simple', '退货 | 退款')
        LIMIT 10
    """)
    old_time = (time.time() - start) * 1000
    old_count = len(cur.fetchall())
    
    # New way (pre-computed)
    start = time.time()
    cur.execute("""
        SELECT id FROM knowledge_chunks 
        WHERE content_tsv @@ to_tsquery('simple', '退货 | 退款')
        LIMIT 10
    """)
    new_time = (time.time() - start) * 1000
    new_count = len(cur.fetchall())
    
    print(f"\n性能对比:")
    print(f"  旧方式 (on-the-fly): {old_time:.1f}ms, {old_count} 结果")
    print(f"  新方式 (物化列):     {new_time:.1f}ms, {new_count} 结果")
    print(f"  加速: {old_time/new_time:.1f}x")
    
    conn.close()
    print("\n完成！")

if __name__ == '__main__':
    main()
