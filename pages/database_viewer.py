"""
数据库查看页面
"""
import streamlit as st
import logging

logger = logging.getLogger(__name__)


def render(st_state: dict):
    st.title("📊 数据库管理")

    sqlite = st_state.get('sqlite_client')
    if not sqlite:
        st.error("数据库未初始化")
        return

    total_cards = sqlite.get_total_cards()
    companies = sqlite.get_companies()
    positions = sqlite.get_positions()

    col1, col2, col3 = st.columns(3)
    col1.metric("卡片总数", total_cards)
    col2.metric("公司数", len(companies))
    col3.metric("岗位数", len(positions))

    st.divider()

    col_search, col_company, col_difficulty = st.columns([3, 2, 2])
    with col_search:
        search_keyword = st.text_input("🔍 搜索关键词", key="db_search")
    with col_company:
        selected_company = st.selectbox("公司", ["全部"] + companies, key="db_company")
    with col_difficulty:
        selected_difficulty = st.selectbox("难度", ["全部", "低", "中", "高"], key="db_difficulty")

    all_cards = sqlite.get_all_cards()

    filtered = all_cards
    if search_keyword:
        kw = search_keyword.lower()
        filtered = [c for c in filtered if kw in c.question.lower() or kw in c.answer.lower()]
    if selected_company != "全部":
        filtered = [c for c in filtered if c.company == selected_company]
    if selected_difficulty != "全部":
        filtered = [c for c in filtered if c.difficulty == selected_difficulty]

    st.divider()
    st.markdown(f"共 **{len(filtered)}** 条结果")

    page_size = st.selectbox("每页显示", [10, 20, 50], index=0, key="db_page_size")
    total_pages = max(1, (len(filtered) + page_size - 1) // page_size)

    if 'db_page' not in st.session_state:
        st.session_state.db_page = 1

    current_page = min(st.session_state.db_page, total_pages)
    st.session_state.db_page = current_page

    start_idx = (current_page - 1) * page_size
    end_idx = min(start_idx + page_size, len(filtered))
    page_cards = filtered[start_idx:end_idx]

    for i, card in enumerate(page_cards):
        global_idx = start_idx + i + 1
        with st.expander(f"{global_idx}. [{card.tags[0] if card.tags else '通用'}] {card.question}"):
            st.markdown(f"**公司**: {card.company} | **岗位**: {card.position} | **难度**: {card.difficulty}")
            st.divider()
            st.markdown(card.answer)
            if card.tags:
                st.caption(f"标签: {', '.join(card.tags)}")
            if card.source_url:
                st.caption(f"来源: {card.source_url}")

    col_prev, col_info, col_next = st.columns([1, 3, 1])
    with col_info:
        st.write(f"第 {start_idx + 1}-{end_idx} 条，共 {len(filtered)} 条")
    with col_prev:
        if current_page > 1:
            if st.button("← 上一页"):
                st.session_state.db_page = current_page - 1
                st.rerun()
    with col_next:
        if current_page < total_pages:
            if st.button("下一页 →"):
                st.session_state.db_page = current_page + 1
                st.rerun()
