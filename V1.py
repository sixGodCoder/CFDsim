import streamlit as st
import random
import time
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# ==========================================
# 1. 深度配置与状态
# ==========================================
st.set_page_config(page_title="CFD 学术生存 V3.0", page_icon="⚓", layout="wide")

# 样式优化：暗黑学术风
st.markdown("""
<style>
    .reportview-container { background: #0e1117; }
    .sidebar .sidebar-content { background: #262730; }
    .big-font { font-size:20px !important; font-family: 'Consolas'; color: #00ff00; }
    .error-font { font-family: 'Courier New'; color: #ff4b4b; }
    .stButton>button { width: 100%; border-radius: 5px; }
</style>
""", unsafe_allow_html=True)

if 'user' not in st.session_state:
    st.session_state.user = {
        'day': 1,
        'funds': 10000,  # 科研经费
        'sanity': 100,  # SAN值
        'hair': 100,  # 发量
        'citations': 0,  # 引用量 (核心积分)
        'hpc_credits': 500,  # 机时 (核心资源)
        'skills': {'mesh': 10, 'numerics': 10, 'writing': 5}
    }
    st.session_state.project = None
    st.session_state.logs = []
    st.session_state.history_residuals = []


# ==========================================
# 2. 类定义：更复杂的项目结构
# ==========================================

class Project:
    def __init__(self, name, model_type, difficulty):
        self.name = name
        self.model_type = model_type  # 'Resistance', 'Seakeeping', 'Damaged'
        self.difficulty = difficulty

        # 创新配置 (Player选择)
        self.turbulence = "k-epsilon"  # 默认
        self.method = "VOF"
        self.innovation = "None"

        # 求解器状态
        self.progress = 0
        self.residuals = []
        self.cfl_history = []
        self.is_diverged = False
        self.error_msg = ""

        # 结果质量
        self.accuracy = 0
        self.novelty_score = 0

    # ==========================================


# 3. 核心逻辑函数
# ==========================================

def add_log(msg, level="info"):
    icon = "ℹ️"
    if level == "error":
        icon = "🔥"
    elif level == "success":
        icon = "✅"
    elif level == "warning":
        icon = "⚠️"
    st.session_state.logs.insert(0, f"[{st.session_state.user['day']}天] {icon} {msg}")


def calculate_stability(proj, cfl):
    # 稳定性核心公式
    # 基础难度
    risk = proj.difficulty * 5

    # 湍流模型风险
    if proj.turbulence == "k-omega SST":
        risk += 5
    elif proj.turbulence == "IDDES":
        risk += 25  # 极难收敛
    elif proj.turbulence == "LES":
        risk += 40

    # 创新点风险
    if proj.innovation == "Overset Mesh (重叠网格)":
        risk += 15
    elif proj.innovation == "6-DOF Motion":
        risk += 20
    elif proj.innovation == "Damaged Compartment (破舱)":
        risk += 30

    # 技能修正
    skill_mitigation = st.session_state.user['skills']['numerics'] * 1.5

    # CFL 放大系数
    cfl_factor = cfl ** 2  # CFL 越大，风险指数级上升

    diverge_prob = (risk * cfl_factor - skill_mitigation) / 1000
    return max(0.01, diverge_prob)


def run_solver_step(cfl_input):
    p = st.session_state.project
    u = st.session_state.user

    # 扣除机时
    cost = 10 if p.turbulence == "RANS" else 50
    if u['hpc_credits'] < cost:
        return "no_credits"
    u['hpc_credits'] -= cost

    # 计算风险
    diverge_prob = calculate_stability(p, cfl_input)

    # 随机判定发散
    if random.random() < diverge_prob:
        p.is_diverged = True
        errors = [
            "Floating Point Exception: Overflow",
            "Negative Volume in Cell ID: 45210",
            "SIGSEGV: Segmentation Fault",
            "Divergence detected in AMG solver"
        ]
        p.error_msg = random.choice(errors)
        p.residuals.append(5.0)  # 残差飙升
        return "diverged"

    # 正常收敛逻辑
    last_res = p.residuals[-1] if p.residuals else -1.0
    # 收敛速度与 CFL 成正比
    speed = cfl_input * (1 + u['skills']['numerics'] / 20)
    p.progress += speed

    # 残差波动
    noise = np.random.normal(0, 0.1 * cfl_input)
    trend = -0.05 if p.progress < 80 else -0.01  # 后期难以在大下降
    new_res = max(-6, last_res + trend + noise)

    p.residuals.append(new_res)
    p.cfl_history.append(cfl_input)

    if p.progress >= 100:
        return "completed"
    return "running"


def submit_paper():
    p = st.session_state.project
    u = st.session_state.user

    # 论文质量评分 = 创新分 + 精度分 + 写作技能
    paper_quality = p.novelty_score + (100 + p.residuals[-1] * 10) + u['skills']['writing']

    # 审稿人心情 (RNG)
    reviewer_mood = random.randint(-20, 20)
    final_score = paper_quality + reviewer_mood

    threshold = 80 + (p.difficulty * 5)

    if final_score >= threshold:
        impact = int(p.novelty_score * 2 + random.randint(10, 50))
        u['citations'] += impact
        u['funds'] += impact * 100
        add_log(f"Paper Accepted! 发表在 JFM/Ocean Eng. 引用+{impact}, 经费到账。", "success")
    else:
        reasons = [
            "Reviewer #2: '缺乏网格无关性验证。'",
            "Reviewer #2: '创新点不足，建议转投 Open Access。'",
            "Reviewer #2: '实验数据对比误差太大。'",
            "Editor: '不在本刊收录范围内。'"
        ]
        u['sanity'] -= 15
        add_log(f"拒稿 (Rejected). {random.choice(reasons)}", "error")

    st.session_state.project = None


# ==========================================
# 4. 界面构建
# ==========================================

# --- 侧边栏 ---
with st.sidebar:
    st.title("🎓 博士生面板")
    u = st.session_state.user

    col1, col2 = st.columns(2)
    col1.metric("H-Index", int(u['citations'] / 10))
    col2.metric("引用量", u['citations'])

    st.metric("经费 (RMB)", f"¥{u['funds']}")
    st.progress(u['sanity'] / 100, text=f"SAN值: {u['sanity']}")
    st.progress(u['hair'] / 100, text=f"发量: {u['hair']}%")
    st.metric("HPC 机时", f"{u['hpc_credits']} core-hrs")

    st.divider()
    if st.button("购买机时 (¥2000/500hrs)"):
        if u['funds'] >= 2000:
            u['funds'] -= 2000
            u['hpc_credits'] += 500
            add_log("充值了超算中心机时。")
            st.rerun()

    if st.button("参加学术会议 (SAN+20, 经费-5000)"):
        if u['funds'] >= 5000:
            u['funds'] -= 5000
            u['sanity'] = min(100, u['sanity'] + 20)
            u['skills']['writing'] += 2  # 社交提升写作？
            add_log("在夏威夷开了个水会，心情大好。")
            st.rerun()

# --- 主界面 ---
st.title("⚓ CFD Academic Survival: DTMB 5415 Edition")

if u['sanity'] <= 0 or u['hair'] <= 0:
    st.error("GAME OVER. 你因压力过大退学了。")
    if st.button("重读博士"):
        st.session_state.clear()
        st.rerun()
    st.stop()

# 选项卡
tab_proposal, tab_solver, tab_post = st.tabs(["📑 项目立项 (Proposal)", "🖥️ 求解器 (Solver)", "📈 后处理 (Post)"])

# === TAB 1: 立项 ===
with tab_proposal:
    if st.session_state.project is None:
        st.subheader("撰写新的研究计划")

        # 1. 选择船型工况
        col1, col2 = st.columns(2)
        with col1:
            base_case = st.selectbox("研究对象 (Hull Form)",
                                     ["DTMB 5415 (静水阻力)", "DTMB 5415 (规则波)", "DTMB 5415 (破损稳性/Damaged)"])

        # 2. 选择数值方法 (组合创新)
        with col2:
            turb_model = st.selectbox("湍流模型",
                                      ["k-epsilon (RANS)", "k-omega SST (RANS)", "IDDES (Hybrid)", "LES (高保真)"])

        st.write("### 添加创新点 (Innovation Points)")
        st.caption("创新点越多，论文越容易中，但越难算。")

        innovations = st.multiselect("选择数值创新技术",
                                     ["Overset Mesh (重叠网格)", "VOF-to-DPM (多相流转换)", "6-DOF Motion (自航)",
                                      "Active Fin Stabilizer (减摇鳍)"])

        # 计算难度预览
        base_diff = {"DTMB 5415 (静水阻力)": 2, "DTMB 5415 (规则波)": 5, "DTMB 5415 (破损稳性/Damaged)": 9}[base_case]
        innov_score = len(innovations) * 10
        if "IDDES" in turb_model: innov_score += 15
        if "LES" in turb_model: innov_score += 30

        est_difficulty = base_diff + len(innovations) * 2
        st.info(f"预计难度系数: {est_difficulty} | 预计学术价值: {innov_score + base_diff * 5}")

        if st.button("提交开题报告 (Start Project)"):
            new_proj = Project(base_case, base_case, est_difficulty)
            new_proj.turbulence = turb_model
            new_proj.innovation = ", ".join(innovations) if innovations else "None"
            new_proj.novelty_score = innov_score + base_diff * 5
            st.session_state.project = new_proj
            add_log(f"项目启动: {base_case} using {turb_model}")
            st.rerun()
    else:
        st.info("当前已有项目正在进行，请前往【求解器】页面。")
        if st.button("删库跑路 (放弃项目)"):
            st.session_state.project = None
            u['sanity'] += 5
            add_log("放弃了项目，虽然可耻但有用。")
            st.rerun()

# === TAB 2: 求解器 ===
with tab_solver:
    proj = st.session_state.project
    if proj:
        st.subheader(f"正在计算: {proj.name}")
        st.caption(f"配置: {proj.turbulence} | 创新: {proj.innovation}")

        # 布局
        g_col1, g_col2 = st.columns([3, 1])

        with g_col1:
            # 实时残差图 (使用 Plotly)
            if proj.residuals:
                fig = make_subplots(specs=[[{"secondary_y": True}]])

                # 残差线
                fig.add_trace(
                    go.Scatter(y=proj.residuals, mode='lines', name='Residuals (log)', line=dict(color='#00ff00')),
                    secondary_y=False)
                # CFL 线
                fig.add_trace(go.Scatter(y=proj.cfl_history, mode='lines', name='CFL Number',
                                         line=dict(color='yellow', dash='dot')), secondary_y=True)

                fig.update_layout(title="Solver Monitor", template="plotly_dark", height=350,
                                  margin=dict(l=20, r=20, t=40, b=20))
                fig.update_yaxes(title_text="Log Residual", range=[-7, 10], secondary_y=False)
                fig.update_yaxes(title_text="CFL", range=[0, 10], secondary_y=True)

                st.plotly_chart(fig, use_container_width=True)
            else:
                st.write("等待初始化...")
                st.image("https://media.giphy.com/media/3o7bu3XilJ5BOiSGic/giphy.gif",
                         width=200)  # Loading GIF placeholder

        with g_col2:
            st.write("### 控制台")
            st.progress(min(100, int(proj.progress)), text=f"物理时间: {int(proj.progress)}%")

            # 核心玩法：CFL 调节
            cfl_val = st.slider("CFL Number (Courant数)", 0.1, 5.0, 1.0, help="CFL越大算得越快，但容易发散。")

            # 操作按钮
            if not proj.is_diverged and proj.progress < 100:
                if st.button("迭代 (Run 50 Steps)"):
                    with st.spinner("Solving N-S Equations..."):
                        time.sleep(0.5)  # 模拟计算延迟
                        status = run_solver_step(cfl_val)

                        if status == "diverged":
                            add_log(f"计算崩溃! {proj.error_msg}", "error")
                            u['hair'] -= 5
                        elif status == "no_credits":
                            st.error("机时不足！请去充值。")
                        elif status == "completed":
                            add_log("计算收敛完成！", "success")

                        st.rerun()

            # 发散后的处理
            if proj.is_diverged:
                st.error(f"❌ 错误: {proj.error_msg}")
                if st.button("降低松弛因子重试 (Under-Relaxation)"):
                    proj.is_diverged = False
                    proj.residuals.append(proj.residuals[-1] - 2)  # 强行压残差
                    add_log("调整 URF 试图挽救...", "warning")
                    st.rerun()
                if st.button("放弃并重置"):
                    st.session_state.project = None
                    st.rerun()

            # 完成后的处理
            if proj.progress >= 100:
                st.success("计算完成！")
                st.info("请前往【后处理】页面撰写论文。")

    else:
        st.warning("请先在【项目立项】页面创建项目。")

# === TAB 3: 后处理 ===
with tab_post:
    if st.session_state.project and st.session_state.project.progress >= 100:
        proj = st.session_state.project
        st.subheader("📊 结果分析 & 投稿")

        # 模拟生成云图
        col_res1, col_res2 = st.columns(2)
        with col_res1:
            st.write("### 自由液面波高 (VOF)")
            # 假装生成一个波形图
            x = np.linspace(0, 10, 100)
            y = np.sin(x) * (1 - 0.1 * random.random())
            fig_wave = go.Figure(data=go.Scatter(x=x, y=y, fill='tozeroy'))
            fig_wave.update_layout(title="Free Surface Elevation", template="plotly_dark", height=200)
            st.plotly_chart(fig_wave, use_container_width=True)

        with col_res2:
            st.write("### 论文草稿预览")
            st.code(f"""
            Title: Numerical Simulation of {proj.name} 
            Method: {proj.turbulence} with {proj.innovation}

            Abstract:
            In this paper, the seakeeping performance of DTMB 5415
            is investigated using {proj.method}. Results show that...
            """, language='latex')

        st.write("---")
        st.write("### 投稿决策")
        st.write("选择目标期刊：")

        target = st.radio("Target Journal",
                          ["Journal of Hydrodynamics (IF: 2.5)", "Ocean Engineering (IF: 4.0)", "JFM (IF: 4.5)"])

        if st.button("Submit Paper (点击投稿)"):
            with st.spinner("Reviewer #2 is reading your manuscript..."):
                time.sleep(2)
                submit_paper()
                st.rerun()
    else:
        st.info("暂无待处理数据。")

# --- 底部日志 ---
st.write("---")
st.caption("System Logs:")
log_txt = "\n".join(st.session_state.logs)
st.text_area("", log_txt, height=100)