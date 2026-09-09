"""
Streamlit 应用入口
"""
import os
import streamlit as st
import logging
import logging.config
import yaml
from pathlib import Path
from typing import Optional

from src.config import load_settings, Settings
from src.storage import SQLiteClient, ChromaClient
from src.core import HeartbeatDriver, RecommendationEngine, LLMAuditor
from src.core.user_memory import UserMemoryModule
from src.core.embedding_provider import EmbeddingConfig, EmbeddingProviderFactory
from src.core.llm_client import LLMClient
from src.core.email_notifier import EmailNotifier
from src.core.preference_store import UserPreferenceStore
from src.core.context_store import ContextStore
from src.core.context_manager import ContextManager
from src.core.daily_mission import DailyMissionManager
from src.core.rag_manager import RagManager
from src.workflow import CollectionOrchestrator, CollectorWorkflow, AnalyzerWorkflow, SchedulerWorkflow
from src.agents.learning_router import LearningRouter
from src.agents.anxiety_agent import AnxietyReliefAgent
from src.agents.card_quiz_agent import CardQuizAgent
from src.agents.interview_agent import InterviewSimAgent


def setup_logging(config_path: Optional[str | Path] = None):
    """配置日志"""
    if config_path is None:
        config_path = Path(__file__).parent / "logging.yaml"
    
    if Path(config_path).exists():
        with open(config_path, 'r', encoding='utf-8') as f:
            log_config = yaml.safe_load(f)
            logging.config.dictConfig(log_config)
    else:
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )


setup_logging()
logger = logging.getLogger(__name__)


def init_session_state():
    """初始化 session state"""
    if 'initialized' not in st.session_state:
        st.session_state['initialized'] = False
        st.session_state['supervisor'] = None
        st.session_state['settings'] = None


def init_system():
    """初始化系统"""
    settings = load_settings()
    
    sqlite = SQLiteClient(settings.storage.db_path)
    
    embedding_config = EmbeddingConfig(
        provider=settings.embedding.provider,
        model=settings.embedding.model,
        api_key=settings.embedding.api_key or os.getenv("OPENAI_API_KEY") or os.getenv("COHERE_API_KEY"),
        base_url=settings.embedding.base_url,
        dimension=settings.embedding.dimension
    )
    embedding_provider = EmbeddingProviderFactory.create(embedding_config)
    chroma = ChromaClient(settings.storage.chroma_path, embedding_provider=embedding_provider)
    
    collector = CollectorWorkflow(
        keywords=settings.crawler.keywords,
        max_per_keyword=settings.crawler.max_per_keyword,
        days_range=settings.crawler.days_range
    )
    
    analyzer = AnalyzerWorkflow(
        api_key=settings.llm.api_key,
        base_url=settings.llm.base_url,
        model=settings.llm.model,
        duplicate_threshold=settings.analyzer.duplicate_threshold,
        similar_threshold=settings.analyzer.similar_threshold,
        companies=settings.analyzer.companies,
        positions=settings.analyzer.positions
    )
    
    recommendation = RecommendationEngine(
        sqlite_client=sqlite,
        weights={
            'retrievability': settings.recommendation.weights.retrievability,
            'weakness': settings.recommendation.weights.weakness,
            'hotness': settings.recommendation.weights.hotness,
            'dependency': settings.recommendation.weights.dependency
        },
        diversity_penalty_coef=settings.recommendation.diversity_penalty_coef,
        recently_shown_tags_length=settings.recommendation.recently_shown_tags_length
    )
    
    auditor = None
    if settings.llm.api_key:
        auditor = LLMAuditor(
            api_key=settings.llm.api_key,
            model=settings.llm.model,
            consecutive_errors_threshold=settings.audit.consecutive_errors,
            error_rate_threshold=settings.audit.error_rate
        )
    
    heartbeat = HeartbeatDriver(
        scheduled_times=settings.heartbeat.scheduled_times,
        cooldown_minutes=settings.heartbeat.cooldown_on_error
    )
    
    user_memory = UserMemoryModule(memory_dir=str(Path("./memory").absolute()))
    
    scheduler = SchedulerWorkflow(
        sqlite_client=sqlite,
        chroma_client=chroma,
        recommendation_engine=recommendation,
        llm_auditor=auditor,
        keywords=settings.crawler.keywords,
        user_memory=user_memory
    )
    
    pref_store = UserPreferenceStore()
    email_notifier = EmailNotifier({
        "enabled": settings.email.enabled,
        "smtp_host": settings.email.smtp_host,
        "smtp_port": settings.email.smtp_port,
        "smtp_user": settings.email.smtp_user,
        "smtp_password": settings.email.smtp_password,
        "from_name": settings.email.from_name,
        "to": settings.email.to,
    })

    supervisor = CollectionOrchestrator(
        sqlite_client=sqlite,
        chroma_client=chroma,
        collector=collector,
        analyzer=analyzer,
        scheduler=scheduler,
        heartbeat=heartbeat,
        llm_auditor=auditor,
        user_memory=user_memory,
        preference_store=pref_store,
        email_notifier=email_notifier,
    )

    return supervisor, settings, user_memory, sqlite, chroma, pref_store, email_notifier


def main():
    st.set_page_config(
        page_title="面试猎手",
        page_icon="🎯",
        layout="wide"
    )
    
    init_session_state()
    
    if not st.session_state['initialized']:
        try:
            supervisor, settings, user_memory, sqlite, chroma, pref_store, email_notifier = init_system()

            st.session_state['supervisor'] = supervisor
            st.session_state['settings'] = settings
            st.session_state['user_memory'] = user_memory
            st.session_state['sqlite_client'] = sqlite
            st.session_state['chroma_client'] = chroma
            st.session_state['preference_store'] = pref_store

            llm = LLMClient(
                api_key=settings.llm.api_key,
                base_url=settings.llm.base_url,
                model=settings.llm.model,
            )
            st.session_state['llm_client'] = llm

            context_store = ContextStore()
            st.session_state['context_store'] = context_store

            context_mgr = ContextManager(context_store, llm)
            st.session_state['context_manager'] = context_mgr

            daily_mgr = DailyMissionManager(sqlite)
            st.session_state['daily_mission'] = daily_mgr

            rag_mgr = RagManager(chroma, sqlite)
            st.session_state['rag_manager'] = rag_mgr

            router = LearningRouter(llm, pref_store)
            st.session_state['learning_router'] = router

            anxiety = AnxietyReliefAgent(llm)
            st.session_state['anxiety_agent'] = anxiety

            quiz = CardQuizAgent(llm, rag_mgr, sqlite)
            st.session_state['card_quiz_agent'] = quiz

            interview = InterviewSimAgent(llm, rag_mgr)
            st.session_state['interview_agent'] = interview
            
            import asyncio
            try:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                loop.run_until_complete(supervisor.initialize())
            except Exception as e:
                logger.error(f"初始化失败: {e}")
            
            st.session_state['initialized'] = True
            
        except Exception as e:
            st.error(f"系统初始化失败: {e}")
            logger.error(f"初始化错误: {e}")
            return
    
    st.sidebar.title("🎯 面试猎手")
    st.sidebar.markdown("---")
    
    page = st.sidebar.radio(
        "导航",
        ["📚 今日学习", "💬 对话学习", "📊 知识库", "🗄️ 数据库", "⚙️ 系统设置"],
        index=0
    )
    
    st_state = {
        'supervisor': st.session_state['supervisor'],
        'settings': st.session_state['settings'],
        'session_state': st.session_state,
        'user_memory': st.session_state.get('user_memory'),
        'llm_client': st.session_state.get('llm_client'),
        'preference_store': st.session_state.get('preference_store'),
        'context_store': st.session_state.get('context_store'),
        'context_manager': st.session_state.get('context_manager'),
        'daily_mission': st.session_state.get('daily_mission'),
        'rag_manager': st.session_state.get('rag_manager'),
        'learning_router': st.session_state.get('learning_router'),
        'anxiety_agent': st.session_state.get('anxiety_agent'),
        'card_quiz_agent': st.session_state.get('card_quiz_agent'),
        'interview_agent': st.session_state.get('interview_agent'),
        'sqlite_client': st.session_state.get('sqlite_client'),
        'chroma_client': st.session_state.get('chroma_client'),
    }
    
    if page == "📚 今日学习":
        from pages.todays_mission import render
        render(st_state)
    
    elif page == "💬 对话学习":
        from pages.chat_learning import render
        render(st_state)
    
    elif page == "📊 知识库":
        from pages.knowledge_insights import render
        render(st_state)

    elif page == "🗄️ 数据库":
        from pages.database_viewer import render
        render(st_state)
    
    elif page == "⚙️ 系统设置":
        from pages.control_center import render
        render(st_state)


if __name__ == "__main__":
    main()
