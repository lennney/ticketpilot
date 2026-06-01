#!/usr/bin/env python3
"""Insert cross-border e-commerce knowledge entries into TicketPilot database."""

import json
import hashlib
import os
import sys
from pathlib import Path

# Load DB password
env_path = Path(__file__).parent.parent.parent / '.env.local'
if env_path.exists():
    for line in env_path.read_text().splitlines():
        if line.startswith('DB_PASSWORD='):
            os.environ['DB_PASSWORD'] = line.split('=', 1)[1].strip()

DB_PASSWORD = os.environ.get('DB_PASSWORD', '')

import psycopg

def content_hash(text: str) -> str:
    return hashlib.sha256(text.encode('utf-8')).hexdigest()[:64]

def main():
    json_path = Path(__file__).parent / 'cross_border_structured.json'
    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    faq_entries = data.get('faq_entries', [])
    policy_entries = data.get('policy_entries', [])
    case_entries = data.get('case_entries', [])

    print(f"Loaded: {len(faq_entries)} FAQ, {len(policy_entries)} Policy, {len(case_entries)} Case")

    conn = psycopg.connect(
        host='localhost',
        port=5432,
        dbname='ticketpilot',
        user='ticketpilot',
        password=DB_PASSWORD
    )
    cur = conn.cursor()

    faq_inserted = 0
    pol_inserted = 0
    cas_inserted = 0
    chk_inserted = 0

    # Insert FAQ entries
    for entry in faq_entries:
        try:
            cur.execute("""
                INSERT INTO knowledge_faq (business_domain, title, content, intent_tags)
                VALUES (%s, %s, %s, %s)
                RETURNING id
            """, (
                entry['domain'],
                entry['title'],
                entry['content'],
                entry.get('intent_tags', [])
            ))
            faq_id = cur.fetchone()[0]
            faq_inserted += 1

            # Insert corresponding chunk
            h = content_hash(entry['content'])
            cur.execute("""
                INSERT INTO knowledge_chunks (doc_type, business_domain, content, content_hash, source_table, source_id)
                VALUES (%s, %s, %s, %s, %s, %s)
            """, (
                'faq',
                entry['domain'],
                entry['content'],
                h,
                'knowledge_faq',
                str(faq_id)
            ))
            chk_inserted += 1
        except Exception as e:
            print(f"  FAQ error [{entry['title'][:30]}]: {e}")
            conn.rollback()
            conn = psycopg.connect(host='localhost', port=5432, dbname='ticketpilot', user='ticketpilot', password=DB_PASSWORD)
            cur = conn.cursor()

    # Insert Policy entries
    for entry in policy_entries:
        try:
            cur.execute("""
                INSERT INTO knowledge_policy (business_domain, policy_code, title, content, effective_date)
                VALUES (%s, %s, %s, %s, %s)
                RETURNING id
            """, (
                entry['domain'],
                entry['policy_code'],
                entry['title'],
                entry['content'],
                entry.get('effective_date', '2024-01-01')
            ))
            pol_id = cur.fetchone()[0]
            pol_inserted += 1

            h = content_hash(entry['content'])
            cur.execute("""
                INSERT INTO knowledge_chunks (doc_type, business_domain, content, content_hash, source_table, source_id)
                VALUES (%s, %s, %s, %s, %s, %s)
            """, (
                'policy',
                entry['domain'],
                entry['content'],
                h,
                'knowledge_policy',
                str(pol_id)
            ))
            chk_inserted += 1
        except Exception as e:
            print(f"  Policy error [{entry['title'][:30]}]: {e}")
            conn.rollback()
            conn = psycopg.connect(host='localhost', port=5432, dbname='ticketpilot', user='ticketpilot', password=DB_PASSWORD)
            cur = conn.cursor()

    # Insert Case entries
    for entry in case_entries:
        try:
            cur.execute("""
                INSERT INTO knowledge_case (business_domain, case_id, issue_summary, resolution, risk_level, compensation_amount)
                VALUES (%s, %s, %s, %s, %s, %s)
                RETURNING id
            """, (
                entry['domain'],
                entry['case_id'],
                entry['issue_summary'],
                entry['resolution'],
                entry.get('risk_level', 'medium'),
                entry.get('compensation_amount', 0)
            ))
            cas_id = cur.fetchone()[0]
            cas_inserted += 1

            h = content_hash(entry['issue_summary'] + entry['resolution'])
            cur.execute("""
                INSERT INTO knowledge_chunks (doc_type, business_domain, content, content_hash, source_table, source_id)
                VALUES (%s, %s, %s, %s, %s, %s)
            """, (
                'case',
                entry['domain'],
                entry['issue_summary'] + ' ' + entry['resolution'],
                h,
                'knowledge_case',
                str(cas_id)
            ))
            chk_inserted += 1
        except Exception as e:
            print(f"  Case error [{entry['case_id']}]: {e}")
            conn.rollback()
            conn = psycopg.connect(host='localhost', port=5432, dbname='ticketpilot', user='ticketpilot', password=DB_PASSWORD)
            cur = conn.cursor()

    conn.commit()

    # Verify
    cur2 = conn.cursor()
    cur2.execute('SELECT count(*) FROM knowledge_faq')
    total_faq = cur2.fetchone()[0]
    cur2.execute('SELECT count(*) FROM knowledge_policy')
    total_pol = cur2.fetchone()[0]
    cur2.execute('SELECT count(*) FROM knowledge_case')
    total_cas = cur2.fetchone()[0]
    cur2.execute('SELECT count(*) FROM knowledge_chunks')
    total_chk = cur2.fetchone()[0]

    print(f"\n=== INSERTION RESULTS ===")
    print(f"Inserted: {faq_inserted} FAQ + {pol_inserted} Policy + {cas_inserted} Case = {faq_inserted + pol_inserted + cas_inserted} total")
    print(f"Chunks inserted: {chk_inserted}")
    print(f"\nDatabase totals:")
    print(f"  FAQ: {total_faq}")
    print(f"  Policy: {total_pol}")
    print(f"  Case: {total_cas}")
    print(f"  Chunks: {total_chk}")
    print(f"  Grand total entries: {total_faq + total_pol + total_cas}")

    conn.close()

if __name__ == '__main__':
    main()
