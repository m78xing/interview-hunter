"""
系统设置页面
"""
import streamlit as st


def render(st_state: dict):
    """渲染系统设置页面"""
    
    st.title("⚙️ 系统设置")
    
    supervisor = st_state.get('supervisor')
    if not supervisor:
        st.error("系统未初始化")
        return
    
    settings = st_state.get('settings')
    
    st.divider()
    
    st.subheader("🎯 学习目标")
    
    target_company = st.text_input(
        "目标公司",
        value=settings.user.target_company if settings else '字节跳动',
        help="设置你目标的公司，Agent 会优先推荐相关面经"
    )
    
    target_position = st.text_input(
        "目标岗位",
        value=settings.user.target_position if settings else '算法岗',
        help="设置你目标的岗位"
    )
    
    daily_goal = st.number_input(
        "每日目标",
        min_value=1,
        max_value=100,
        value=settings.user.daily_goal if settings else 20,
        help="每天计划复习的卡片数量"
    )
    
    if st.button("💾 保存学习目标"):
        st.success("学习目标已保存！")
    
    st.divider()
    
    st.subheader("🔍 爬虫关键字")
    
    current_keywords = settings.crawler.keywords if settings else []
    
    st.write("当前监控的关键字：")
    
    for kw in current_keywords:
        col1, col2 = st.columns([4, 1])
        with col1:
            st.text_input("关键字", value=kw, key=f"kw_{kw}", disabled=True, label_visibility="collapsed")
        with col2:
            if st.button("🗑️", key=f"del_{kw}"):
                supervisor.remove_keyword(kw)
                current_keywords.remove(kw)
                st.rerun()
    
    st.divider()
    
    col1, col2 = st.columns(2)
    
    with col1:
        new_keyword = st.text_input("添加新关键字", placeholder="输入关键字...")
        
        if st.button("➕ 添加", disabled=not new_keyword):
            if new_keyword not in current_keywords:
                supervisor.add_keyword(new_keyword)
                current_keywords.append(new_keyword)
                st.success(f"已添加: {new_keyword}")
                st.rerun()
            else:
                st.warning("关键字已存在")
    
    with col2:
        st.write("")
        st.write("")
        
        if st.button("🔄 强制同步（手动触发采集）", use_container_width=True):
            with st.spinner("正在采集..."):
                import asyncio
                try:
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    loop.run_until_complete(supervisor._run_collection_cycle())
                    st.success("采集完成！")
                except Exception as e:
                    st.error(f"采集失败: {e}")
    
    st.divider()
    
    st.subheader("📊 推荐算法参数")
    
    weights = settings.recommendation.weights if settings else None
    
    col1, col2 = st.columns(2)
    
    with col1:
        retrievability = st.slider(
            "遗忘曲线权重",
            min_value=0.0,
            max_value=1.0,
            value=weights.retrievability if weights else 0.35,
            step=0.05,
            help="根据遗忘曲线推荐久未复习的卡片"
        )
        
        weakness = st.slider(
            "薄弱点权重",
            min_value=0.0,
            max_value=1.0,
            value=weights.weakness if weights else 0.30,
            step=0.05,
            help="优先推荐错误率高的知识点"
        )
    
    with col2:
        hotness = st.slider(
            "岗位热度权重",
            min_value=0.0,
            max_value=1.0,
            value=weights.hotness if weights else 0.20,
            step=0.05,
            help="优先推荐目标公司的热门考点"
        )
        
        dependency = st.slider(
            "知识依赖权重",
            min_value=0.0,
            max_value=1.0,
            value=weights.dependency if weights else 0.15,
            step=0.05,
            help="根据知识点依赖关系推荐前置知识"
        )
    
    if st.button("💾 保存算法参数"):
        st.success("算法参数已保存！")
    
    st.divider()
    
    st.subheader("🔧 系统状态")
    
    status = supervisor.get_status()
    
    col1, col2 = st.columns(2)
    
    with col1:
        heartbeat_status = supervisor.heartbeat.get_status()
        st.json({
            "状态": heartbeat_status.get('state', 'unknown'),
            "连续错误": heartbeat_status.get('consecutive_errors', 0),
            "冷却中": heartbeat_status.get('in_cooldown', False)
        })
    
    with col2:
        stats = status['stats']
        st.json({
            "采集统计": stats['collector'],
            "分析统计": stats['analyzer']
        })
    
    st.divider()
    
    st.subheader("⚠️ 危险操作")
    
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("🗑️ 清空所有卡片", use_container_width=True):
            st.warning("此操作不可恢复！")
    
    with col2:
        if st.button("🔄 重置学习记录", use_container_width=True):
            st.warning("此操作不可恢复！")
    
    st.divider()
    
    st.caption("面试猎手 v0.1.0 | 多 Agent 智能面经学习系统")
