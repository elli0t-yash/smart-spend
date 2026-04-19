"""
Phase 3 – NetworkX merchant knowledge graph.

Builds a weighted co-occurrence graph where:
  - Nodes  = merchants (spend amounts, category, community ID, centrality score)
  - Edges  = two merchants appeared in transactions on the same day (weight = co-occurrence count)

Community detection (greedy modularity) clusters merchants that tend to be used together,
e.g. Swiggy + Zomato form one cluster, Uber + Rapido another.

Degree centrality identifies "hub" merchants — the ones most connected to other merchants.
"""
from __future__ import annotations
from collections import defaultdict
from typing import Any


def build_merchant_graph(transactions: list[dict]) -> dict[str, Any]:
    """
    Build and analyse a merchant co-occurrence graph from a list of transactions.

    Returns a dict with:
        nodes   – list of node descriptors
        edges   – list of edge descriptors
        stats   – high-level summary
        nlp_ready – True (always, signals Phase 3 is active)
    """
    try:
        import networkx as nx
    except ImportError:
        return {"nodes": [], "edges": [], "stats": {}, "nlp_ready": False}

    debits = [t for t in transactions if t["type"] == "debit"]

    # ── Aggregate per merchant ─────────────────────────────────────────────────
    merchant_totals: dict[str, float] = defaultdict(float)
    merchant_counts: dict[str, int] = defaultdict(int)
    merchant_category: dict[str, str] = {}
    by_date: dict[str, list[str]] = defaultdict(list)

    for txn in debits:
        m = txn["merchant"]
        merchant_totals[m] += txn["amount"]
        merchant_counts[m] += 1
        merchant_category.setdefault(m, txn.get("category", "Other"))
        by_date[txn["date"]].append(m)

    # ── Build graph ────────────────────────────────────────────────────────────
    G: nx.Graph = nx.Graph()

    for merchant, total in merchant_totals.items():
        G.add_node(
            merchant,
            total=round(total, 2),
            count=merchant_counts[merchant],
            category=merchant_category.get(merchant, "Other"),
        )

    # Co-occurrence edges (same day → connected)
    for _date, merchants in by_date.items():
        unique = list(set(merchants))
        for i in range(len(unique)):
            for j in range(i + 1, len(unique)):
                u, v = unique[i], unique[j]
                if G.has_edge(u, v):
                    G[u][v]["weight"] += 1
                else:
                    G.add_edge(u, v, weight=1)

    if G.number_of_nodes() == 0:
        return {"nodes": [], "edges": [], "stats": {}, "nlp_ready": True}

    # ── Community detection ────────────────────────────────────────────────────
    try:
        from networkx.algorithms.community import greedy_modularity_communities
        communities = list(greedy_modularity_communities(G))
        for idx, community in enumerate(communities):
            for node in community:
                G.nodes[node]["community"] = idx
    except Exception:
        for node in G.nodes:
            G.nodes[node]["community"] = 0

    # ── Centrality ────────────────────────────────────────────────────────────
    centrality = nx.degree_centrality(G)
    for node, score in centrality.items():
        G.nodes[node]["centrality"] = round(score, 4)

    # ── Serialize ─────────────────────────────────────────────────────────────
    nodes = [
        {
            "id":         node,
            "total":      data["total"],
            "count":      data["count"],
            "category":   data.get("category", "Other"),
            "community":  data.get("community", 0),
            "centrality": data.get("centrality", 0.0),
        }
        for node, data in G.nodes(data=True)
    ]
    edges = [
        {"source": u, "target": v, "weight": d.get("weight", 1)}
        for u, v, d in G.edges(data=True)
    ]

    # ── Stats / insights ──────────────────────────────────────────────────────
    top_by_spend   = sorted(nodes, key=lambda x: x["total"],      reverse=True)[:5]
    most_connected = sorted(nodes, key=lambda x: x["centrality"], reverse=True)[:3]

    num_communities = len({n["community"] for n in nodes})
    community_map: dict[int, list[str]] = defaultdict(list)
    for n in nodes:
        community_map[n["community"]].append(n["id"])

    stats = {
        "total_merchants":   len(nodes),
        "total_connections": len(edges),
        "num_communities":   num_communities,
        "top_by_spend":      [m["id"] for m in top_by_spend],
        "most_connected":    [m["id"] for m in most_connected],
        "communities":       [
            {"id": cid, "members": members}
            for cid, members in sorted(community_map.items())
        ],
    }

    return {
        "nodes":     nodes,
        "edges":     edges,
        "stats":     stats,
        "nlp_ready": True,
    }
