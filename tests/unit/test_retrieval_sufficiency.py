def test_sufficient_retrieval():
    from ticketpilot.retrieval.retrieve_evidence import assess_retrieval_sufficiency

    results = [
        {"content": "chunk1", "score": 0.9, "source": "faq"},
        {"content": "chunk2", "score": 0.85, "source": "policy"},
        {"content": "chunk3", "score": 0.8, "source": "case"},
    ]
    assessment = assess_retrieval_sufficiency(results, min_results=3, min_avg_score=0.7)
    assert assessment["sufficient"] is True
    assert assessment["avg_score"] >= 0.7


def test_insufficient_retrieval():
    from ticketpilot.retrieval.retrieve_evidence import assess_retrieval_sufficiency

    results = [
        {"content": "chunk1", "score": 0.4, "source": "faq"},
    ]
    assessment = assess_retrieval_sufficiency(results, min_results=3, min_avg_score=0.7)
    assert assessment["sufficient"] is False
    assert assessment["reason"] is not None


def test_rewrite_query_expands():
    from ticketpilot.retrieval.retrieve_evidence import rewrite_query

    rewritten = rewrite_query("我的订单没收到 refund")
    assert len(rewritten) > 0


def test_rewrite_query_splits_long():
    from ticketpilot.retrieval.retrieve_evidence import rewrite_query

    long_q = "我想问一下关于订单退款的问题还有物流延迟怎么处理以及退货流程"
    rewritten = rewrite_query(long_q)
    assert len(rewritten) < len(long_q)
