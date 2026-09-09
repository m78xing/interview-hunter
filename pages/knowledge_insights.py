"""
知识库看板页面
"""
import streamlit as st
import plotly.express as px
import pandas as pd


def render(st_state: dict):
    """渲染知识库看板页面"""
    
    st.title("📊 知识库看板")
    
    supervisor = st_state.get('supervisor')
    if not supervisor:
        st.error("系统未初始化")
        return
    
    sqlite = supervisor.sqlite
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        total = sqlite.get_total_cards()
        st.metric("卡片总数", total)
    
    with col2:
        today = sqlite.get_today_review_count()
        st.metric("今日复习", today)
    
    with col3:
        tag_stats = sqlite.get_tag_stats()
        st.metric("标签数", len(tag_stats))
    
    st.divider()
    
    st.subheader("🔥 掌握度热力图")
    
    if tag_stats:
        data = []
        for tag, stats in tag_stats.items():
            data.append({
                '标签': tag,
                '掌握度': stats.get('mastery_level', 0) * 100,
                '复习次数': stats.get('total_reviews', 0),
                '正确数': stats.get('correct_count', 0),
                '错误数': stats.get('error_count', 0)
            })
        
        df = pd.DataFrame(data)
        df = df.sort_values('掌握度', ascending=True)
        
        fig = px.bar(
            df,
            y='标签',
            x='掌握度',
            orientation='h',
            color='掌握度',
            color_continuous_scale=['red', 'yellow', 'green'],
            range_color=[0, 100]
        )
        
        fig.update_layout(
            height=max(300, len(df) * 30),
            showlegend=False,
            xaxis_title='掌握度 (%)',
            yaxis_title=''
        )
        
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("暂无学习数据，继续学习后这里会显示掌握度")
    
    st.divider()
    
    st.subheader("🏷️ 标签详情")
    
    if tag_stats:
        cols = st.columns(3)
        for i, (tag, stats) in enumerate(sorted(tag_stats.items(), key=lambda x: x[1].get('mastery_level', 0))):
            with cols[i % 3]:
                mastery = stats.get('mastery_level', 0) * 100
                
                st.markdown(f"**{tag}**")
                st.progress(mastery / 100, text=f"{mastery:.0f}%")
                
                col1, col2 = st.columns(2)
                with col1:
                    st.caption(f"✓ {stats.get('correct_count', 0)}")
                with col2:
                    st.caption(f"✗ {stats.get('error_count', 0)}")
    
    st.divider()
    
    st.subheader("📈 学习趋势")
    
    review_logs = sqlite.get_recent_review_logs(days=7)
    
    if review_logs:
        logs_data = []
        for log in review_logs:
            try:
                dt = log.reviewed_at[:10]
                logs_data.append({
                    '日期': dt,
                    '质量': log.quality
                })
            except:
                pass
        
        if logs_data:
            df = pd.DataFrame(logs_data)
            daily = df.groupby('日期').agg({
                '质量': ['count', 'mean']
            }).reset_index()
            daily.columns = ['日期', '复习数', '平均质量']
            
            fig = px.line(daily, x='日期', y=['复习数', '平均质量'], markers=True)
            st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("暂无学习趋势数据")
    
    st.divider()
    
    st.subheader("🤖 Agent 状态")
    
    status = supervisor.get_status()
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.json({
            "运行状态": "✓ 运行中" if status['system']['running'] else "✗ 已停止",
            "最后心跳": status['system']['last_heartbeat'] or "无",
            "错误数": len(status['system']['errors'])
        })
    
    with col2:
        st.json({
            "采集器": status['agents']['collector'],
            "分析器": status['agents']['analyzer'],
            "调度器": status['agents']['scheduler']
        })
