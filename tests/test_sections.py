from disclosure_pipeline.sections import locate_sections


def test_heading_variants_and_page_numbers():
    pages = [
        "目录\n业务概要……12\n核心竞争力分析……25",
        "一、业务概要\n这里是正文",
        "二、报告期内公司从事的业务情况\n这里是正文",
        "三、核心竞争力分析\n这里是正文",
        "4. 研发投入情况\n这里是正文",
    ]
    matches = locate_sections(pages)
    assert [(item.section, item.page) for item in matches] == [
        ("业务概况", 2),
        ("业务概况", 3),
        ("核心竞争力", 4),
        ("研发投入", 5),
    ]


def test_long_body_sentence_is_not_a_heading():
    pages = ["报告期内核心竞争力分析表明公司仍需持续投入研发和业务资源。" * 4]
    assert locate_sections(pages, max_heading_length=40) == []
