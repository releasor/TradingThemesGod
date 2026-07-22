from app.scrapers.local_chain import build_chain_groups


def test_build_chain_groups_creates_three_levels_from_constituents():
    """成分股应稳定分配到三层，并生成对应代表公司。"""
    constituents = [
        (1, "公司A"),
        (2, "公司B"),
        (3, "公司C"),
        (4, "公司D"),
        (5, "公司E"),
        (6, "公司F"),
    ]

    groups = build_chain_groups("存储芯片", constituents)

    assert [group["level"] for group in groups] == [
        "upstream",
        "midstream",
        "downstream",
    ]
    assert [group["stock_ids"] for group in groups] == [[1, 2], [3, 4], [5, 6]]
    assert groups[0]["name"] == "存储芯片基础支撑"
    assert groups[1]["representative_companies"] == ["公司C", "公司D"]
    assert "成分股结构推导" in groups[2]["description"]


def test_build_chain_groups_keeps_all_levels_for_small_theme():
    """成分股较少时仍应展示完整三层结构。"""
    groups = build_chain_groups("小题材", [(10, "公司A")])

    assert len(groups) == 3
    assert groups[0]["stock_ids"] == []
    assert groups[1]["stock_ids"] == [10]
    assert groups[2]["stock_ids"] == []


def test_build_chain_groups_deduplicates_representative_company_names():
    """代表公司名称应去重且最多展示五家。"""
    constituents = [(index, "同名公司" if index < 3 else f"公司{index}") for index in range(9)]

    groups = build_chain_groups("测试题材", constituents)

    assert groups[0]["representative_companies"] == ["同名公司"]
    assert all(len(group["representative_companies"]) <= 5 for group in groups)
