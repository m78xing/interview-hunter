"""
对话学习页面
"""
import streamlit as st
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

MODE_LABELS = {
    "anxiety_relief": "焦虑缓解",
    "card_quiz": "卡片问答",
    "interview_sim": "面试模拟",
    "modify_keywords": "关键字更新",
}


def render(st_state: dict):
    st.markdown("## 💬 对话学习")

    llm_client = st_state.get('llm_client')
    learning_router = st_state.get('learning_router')
    anxiety_agent = st_state.get('anxiety_agent')
    card_quiz_agent = st_state.get('card_quiz_agent')
    interview_agent = st_state.get('interview_agent')
    context_manager = st_state.get('context_manager')

    if not all([llm_client, learning_router]):
        st.error("系统未初始化")
        return

    assert learning_router is not None
    assert llm_client is not None

    if 'chat_messages' not in st.session_state:
        st.session_state.chat_messages = []
    if 'session_id' not in st.session_state:
        st.session_state.session_id = f"session_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    if 'interview_active' not in st.session_state:
        st.session_state.interview_active = False
    if 'thinking_placeholder' not in st.session_state:
        st.session_state.thinking_placeholder = None

    main_col, sidebar_col = st.columns([3, 1])

    with sidebar_col:
        st.markdown("### 📋 历史会话")

        if context_manager:
            sessions = context_manager.list_all_sessions()
            current_session = st.session_state.session_id

            for sess in sessions:
                sid = sess["session_id"]
                date_str = sess["created_at"][:10]
                msg_count = sess["message_count"]
                summary = sess.get("summary", "")[:30]

                is_current = sid == current_session
                btn_type = "primary" if is_current else "secondary"

                label = f"{date_str}\n{msg_count}条消息"
                if summary:
                    label += f"\n{summary}"

                if st.button(label, key=f"sess_{sid}", type=btn_type, use_container_width=True):
                    st.session_state.session_id = sid
                    messages = context_manager.load_session_messages(sid)
                    st.session_state.chat_messages = [
                        {"role": m.get("role", "user"), "content": m.get("content", "")}
                        for m in messages
                    ]
                    st.session_state.interview_active = False
                    st.rerun()

            if st.button("➕ 新建会话", use_container_width=True):
                st.session_state.session_id = f"session_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                st.session_state.chat_messages = []
                st.session_state.interview_active = False
                st.rerun()
        else:
            st.caption("上下文管理未初始化")

    with main_col:
        for msg in st.session_state.chat_messages:
            with st.chat_message(msg["role"]):
                st.write(msg["content"])
                if "mode" in msg and msg["role"] == "assistant":
                    mode_label = MODE_LABELS.get(msg["mode"], msg["mode"])
                    st.caption(f"[{mode_label}]")

        user_input = st.chat_input("请输入...")

        if user_input:
            st.session_state.chat_messages.append({"role": "user", "content": user_input})

            route_result = learning_router.route(user_input)
            mode = route_result.get("mode", "anxiety_relief")
            sources = []
            response = ""

            with st.chat_message("assistant"):
                thinking_placeholder = st.empty()
                thinking_placeholder.info("🤔 思考中...")

                thinking_content = ""
                response_content = ""
                response_placeholder = st.empty()

                def on_thinking(chunk: str):
                    nonlocal thinking_content
                    thinking_content += chunk
                    thinking_placeholder.info(f"🤔 思考中...\n\n{thinking_content[-500:]}")

                def on_content(chunk: str):
                    nonlocal response_content
                    response_content += chunk
                    response_placeholder.markdown(response_content)

                if mode == "modify_keywords":
                    keywords = route_result.get("keywords", [])
                    action = route_result.get("action", "none")
                    response = f"已{action}关键字: {keywords}"
                    thinking_placeholder.empty()
                elif mode == "anxiety_relief":
                    if anxiety_agent:
                        response = anxiety_agent.chat_stream(
                            user_message=user_input,
                            on_thinking=on_thinking,
                            on_content=on_content,
                        )
                    else:
                        response = "焦虑缓解模块未初始化"
                        thinking_placeholder.empty()
                elif mode == "card_quiz":
                    if card_quiz_agent:
                        result = card_quiz_agent.chat_stream(
                            user_message=user_input,
                            on_thinking=on_thinking,
                            on_content=on_content,
                        )
                        response = result.get("response", "")
                        sources = result.get("sources", [])
                    else:
                        response = "卡片问答模块未初始化"
                        thinking_placeholder.empty()
                elif mode == "interview_sim":
                    if interview_agent:
                        if not st.session_state.interview_active:
                            if "简历" in user_input or len(user_input) > 50:
                                response = interview_agent.set_resume_stream(
                                    user_input,
                                    on_thinking=on_thinking,
                                    on_content=on_content,
                                )
                                st.session_state.interview_active = True
                            else:
                                response = interview_agent.start_without_resume_stream(
                                    on_thinking=on_thinking,
                                    on_content=on_content,
                                )
                                st.session_state.interview_active = True
                        else:
                            response = interview_agent.handle_answer_stream(
                                user_input,
                                on_thinking=on_thinking,
                                on_content=on_content,
                            )
                    else:
                        response = "面试模拟模块未初始化"
                        thinking_placeholder.empty()
                else:
                    response = llm_client.stream_chat(
                        messages=[{"role": "user", "content": user_input}],
                        on_thinking=on_thinking,
                        on_content=on_content,
                    )
                    thinking_placeholder.empty()

                thinking_placeholder.empty()

                if sources:
                    st.divider()
                    st.markdown("**📄 召回来源**")
                    for i, src in enumerate(sources, 1):
                        sim = src.get("similarity", 0)
                        st.markdown(f"📄 {i}. **{src.get('question', '')}** ({src.get('company', '')} - {src.get('position', '')})  相似度: {sim:.2f}")
                elif mode == "card_quiz":
                    st.info("💡 未找到相关面经，以下回答基于模型自身知识")

                with st.container():
                    mode_label = MODE_LABELS.get(mode, mode)
                    st.caption(f"[{mode_label}]")

            st.session_state.chat_messages.append({
                "role": "assistant",
                "content": response,
                "mode": mode,
            })

            if context_manager:
                context_manager.save_turn(st.session_state.session_id, "user", user_input)
                context_manager.save_turn(st.session_state.session_id, response, "assistant")

            st.rerun()

        if st.session_state.interview_active:
            if st.button("🔚 结束面试"):
                if interview_agent:
                    evaluation = interview_agent.evaluate()
                    st.session_state.chat_messages.append({
                        "role": "assistant",
                        "content": evaluation,
                        "mode": "面试评估",
                    })
                st.session_state.interview_active = False
                if interview_agent:
                    interview_agent.reset()
                st.rerun()

        if st.session_state.chat_messages:
            if st.button("🧹 清空对话"):
                st.session_state.chat_messages = []
                st.rerun()
