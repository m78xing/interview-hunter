"""
每日面经页面
"""
import streamlit as st
import logging
from datetime import date

logger = logging.getLogger(__name__)


def render(st_state: dict):
    st.title("📚 今日面经")

    daily_mission = st_state.get('daily_mission')
    if not daily_mission:
        st.error("每日面经模块未初始化")
        return

    today = date.today().isoformat()
    cards = daily_mission.select_daily_cards()

    col1, col2 = st.columns(2)
    with col1:
        st.metric("今日面经", len(cards))
    with col2:
        st.metric("日期", today)

    st.divider()

    if not cards:
        st.info("暂无面经卡片，请先采集数据")
        return

    for i, card in enumerate(cards):
        if not card:
            continue

        retrievability = "高"
        stats = st_state.get('sqlite_client')
        if stats:
            card_stats = stats.get_card_stats(card.id) or {}
            interval = card_stats.get("interval_days", 0)
            if interval > 7:
                retrievability = "高"
            elif interval > 3:
                retrievability = "中"
            else:
                retrievability = "低"

        with st.expander(f"{i+1}. [{card.tags[0] if card.tags else '通用'}] {card.question}  [遗忘: {retrievability}]"):
            st.markdown(f"**公司**: {card.company} | **岗位**: {card.position} | **难度**: {card.difficulty}")
            st.divider()
            st.markdown(card.answer)
            if card.tags:
                st.caption(f"标签: {', '.join(card.tags)}")

            st.divider()
            st.markdown("**熟悉程度:**")

            familiarity_key = f"familiarity_{card.id}"
            if familiarity_key not in st.session_state:
                st.session_state[familiarity_key] = -1

            current_level = st.session_state[familiarity_key]

            cols = st.columns(5)
            labels = ["😕 陌生", "🤔 模糊", "😐 一般", "😊 熟悉", "🎯 掌握"]
            for level, label in enumerate(labels):
                with cols[level]:
                    if st.button(label, key=f"btn_{card.id}_{level}", type="primary" if current_level == level else "secondary"):
                        st.session_state[familiarity_key] = level
                        daily_mission.record_familiarity(card.id, level)
                        st.rerun()

    st.divider()
    if st.button("🔄 重置今日面经"):
        daily_mission.reset_daily()
        st.rerun()
