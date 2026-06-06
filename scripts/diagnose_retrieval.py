"""诊断检索问题：看实际返回了什么，Precision为什么低。"""
import sys, json, os
sys.path.insert(0, os.path.expanduser("~/ticketpilot/src"))

from dotenv import load_dotenv
load_dotenv(os.path.expanduser("~/ticketpilot/.env"))
load_dotenv(os.path.expanduser("~/ticketpilot/.env.local"), override=True)

from ticketpilot.retrieval import hybrid_retrieval
from ticketpilot.retrieval.providers import get_embedding_provider

# 3个refund相关的测试查询
test_queries = [
    "产品有质量问题，想退款",
    "物流显示已签收但是我没有收到",
    "支付失败但钱被扣了",
]

provider = get_embedding_provider()

for query in test_queries:
    print(f"\n{'='*80}")
    print(f"查询: {query}")
    print('='*80)
    
    trace = hybrid_retrieval(
        query=query,
        top_k=10,
        embedding_provider=provider,
        enable_reranking=True,
    )
    
    # 检查keyword和vector各自的top结果
    print(f"\n[Keyword Top 5]")
    for r in trace.keyword_results[:5]:
        print(f"  rank={r.rank} | {r.doc_type:8s} | {r.content[:80]}...")
    
    print(f"\n[Vector Top 5]")
    for r in trace.vector_results[:5]:
        print(f"  rank={r.rank} | {r.doc_type:8s} | {r.content[:80]}...")
    
    print(f"\n[RRF Fused Top 10]")
    for i, r in enumerate(trace.fused_results[:10], 1):
        kw = f"kw={r.keyword_rank}" if r.keyword_rank else "kw=N/A"
        vec = f"vec={r.vector_rank}" if r.vector_rank else "vec=N/A"
        print(f"  {i:2d}. RRF={r.rrf_score:.6f} | {kw:8s} | {vec:8s} | {r.doc_type:8s} | {r.content[:70]}...")
    
    print(f"\n[Final Evidence IDs]")
    print(f"  {trace.final_evidence_ids[:5]}...")
    print(f"  Latency: {trace.total_latency_ms}ms")
