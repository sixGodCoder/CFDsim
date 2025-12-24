import streamlit as st
import random
import time
import pandas as pd
import numpy as np
import plotly.graph_objects as go

# ==========================================
# 1. 基础配置
# ==========================================
st.set_page_config(page_title="CFD 极速版", page_icon="⚡", layout="centered")

# CSS: 保持大按钮风格，增加一点动效
# CSS: 保持大按钮风格，修改了文字框背景颜色
st.markdown("""
<style>
    .stButton>button {
        width: 100%;
        height: 60px;
        font-size: 18px !important;
        font-weight: bold;
        border-radius: 12px;
        border: 2px solid #333;
        transition: all 0.1s;
    }
    .stButton>button:hover {
        transform: scale(1.02);
        border-color: #00ADB5;
        color: #00ADB5;
    }
    .stButton>button:active {
        transform: scale(0.98);
    }
    .stat-box {
        background: #222;
        color: #fff; /* 确保状态栏文字也是白色的 */
        padding: 10px;
        border-radius: 8px;
        text-align: center;
        border: 1px solid #444;
        margin-bottom: 10px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.3);
    }
    /* 👇👇👇 这里是修改的地方 👇👇👇 */
    .scenario-text {
        font-size: 20px;
        line-height: 1.6;
        margin-bottom: 30px;
        padding: 20px;
        background: #f0f2f6; /* 改成了浅灰色背景，看字更清楚 */
        color: #31333F;      /* 强制文字为深灰色，防止看不见 */
        border-left: 5px solid #00ADB5;
        border-radius: 5px;
    }
    /* 👆👆👆 修改结束 👆👆👆 */
</style>
""", unsafe_allow_html=True)

# ==========================================
# 2. 状态初始化
# ==========================================
if 'init' not in st.session_state:
    st.session_state.init = True
    st.session_state.phase = 'home'  # home, project_select, config, solver, result

    # 玩家属性
    st.session_state.player = {
        'day': 1,
        'hair': 100,
        'sanity': 100,
        'credits': 1000,  # 增加初始机时
        'citations': 0
    }

    # 当前项目
    st.session_state.project = {
        'name': '',
        'difficulty': 0,
        'method': '',
        'innovations': [],
        'progress': 0,
        'residuals': [],
        'is_diverged': False,
        'diverge_reason': ''
    }


# ==========================================
# 3. 逻辑函数
# ==========================================

def change_phase(new_phase):
    st.session_state.phase = new_phase
    st.rerun()


def update_stat(key, value):
    st.session_state.player[key] += value


# 核心计算逻辑：支持一次跑多步 (steps 参数)
def run_solver_batch(mode, steps=1):
    p = st.session_state.project

    # 模式参数定义
    if mode == 'safe':
        cfl = 0.5
        speed = 1.5
        risk = 0.0
        cost = 20
    elif mode == 'normal':
        cfl = 1.0
        speed = 4.0
        risk = 0.02
        cost = 10
    elif mode == 'risky':
        cfl = 5.0
        speed = 12.0
        risk = 0.15 + (p['difficulty'] / 60.0)
        cost = 5

    # 循环执行 steps 次
    for _ in range(steps):
        # 扣费检查
        if st.session_state.player['credits'] < cost:
            return "no_money"

        st.session_state.player['credits'] -= cost
        # 每跑5步过一天
        if random.random() < 0.2:
            st.session_state.player['day'] += 1

        # 判定发散
        innovation_penalty = len(p['innovations']) * 0.03
        final_risk = risk + innovation_penalty

        if random.random() < final_risk:
            p['is_diverged'] = True
            p['diverge_reason'] = random.choice([
                "Negative Volume (网格负体积)",
                "SIGSEGV (段错误)",
                "Divergence in AMG Solver",
                "Floating Point Exception"
            ])
            p['residuals'].append(5.0)  # 爆表
            update_stat('sanity', -10)
            update_stat('hair', -5)
            return "diverged"  # 只要炸一次就停止

        # 进度增加
        p['progress'] += speed

        # 残差模拟
        last_res = p['residuals'][-1] if p['residuals'] else -0.5
        base_drop = -0.15 if cfl < 2 else -0.05
        noise = random.uniform(-0.3, 0.3) * cfl
        new_res = last_res + base_drop + noise
        new_res = max(-7, new_res)  # 下限
        p['residuals'].append(new_res)

        if p['progress'] >= 100:
            return "done"

    return "running"


# ==========================================
# 4. 局部刷新片段 (@st.fragment)
# ==========================================

# ⚠️ 关键点：这个函数里的内容会独立刷新，不会导致整个网页重载
@st.fragment
def solver_dashboard():
    p = st.session_state.project
    pl = st.session_state.player

    # 1. 实时状态栏 (放在这里以保证实时更新)
    c1, c2, c3, c4 = st.columns(4)
    c1.markdown(f"<div class='stat-box'>📅 Day {pl['day']}</div>", unsafe_allow_html=True)
    c2.markdown(f"<div class='stat-box'>💰 机时 {pl['credits']}</div>", unsafe_allow_html=True)
    c3.markdown(f"<div class='stat-box'>🧠 SAN {pl['sanity']}</div>", unsafe_allow_html=True)
    c4.markdown(f"<div class='stat-box'>👴 发量 {pl['hair']}%</div>", unsafe_allow_html=True)

    st.write("---")

    # 2. 绘图区域 (Plotly)
    if p['residuals']:
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            y=p['residuals'],
            mode='lines',
            name='Residual',
            line=dict(color='#00ADB5', width=3)
        ))
        fig.update_layout(
            title=f"残差监视器 (Progress: {int(p['progress'])}%)",
            xaxis_title="Iterations",
            yaxis_title="Log(Residuals)",
            template="plotly_dark",
            height=280,
            margin=dict(l=20, r=20, t=40, b=20),
            yaxis_range=[-8, 8]
        )
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("准备就绪，请选择求解策略开始迭代...")

    # 3. 交互区域
    if p['is_diverged']:
        st.error(f"❌ 计算发散！错误代码: {p['diverge_reason']}")
        c1, c2 = st.columns(2)
        if c1.button("🛠️ 减小松弛因子救一下"):
            p['is_diverged'] = False
            p['residuals'].append(p['residuals'][-1] - 3)
            update_stat('sanity', -10)
            st.rerun()  # 刷新片段

        if c2.button("💥 彻底放弃 (Restart)"):
            p['residuals'] = []
            p['progress'] = 0
            p['is_diverged'] = False
            st.session_state.phase = 'config'  # 修改全局状态
            st.rerun()  # 触发刷新，以便跳出

    elif p['progress'] >= 100:
        st.success("✅ 计算收敛完成！")
        if st.button("📄 提取数据，撰写论文"):
            st.session_state.phase = 'result'
            st.rerun()

    else:
        st.write("请选择迭代策略：")
        c1, c2, c3 = st.columns(3)

        # 策略按钮：不再是跑1步，而是跑N步
        with c1:
            if st.button("🛡️ 苟住 (Safe)\n单步调试"):
                res = run_solver_batch('safe', steps=1)
                if res == "no_money": st.toast("没钱买机时了！")
                st.rerun()

        with c2:
            if st.button("⚖️ 稳健 (Normal)\n连续 5 步"):
                res = run_solver_batch('normal', steps=5)
                if res == "no_money": st.toast("没钱买机时了！")
                st.rerun()

        with c3:
            if st.button("🔥 赌狗 (Risky)\n连续 20 步"):
                res = run_solver_batch('risky', steps=20)
                if res == "no_money": st.toast("没钱买机时了！")
                st.rerun()


# ==========================================
# 5. 主程序流控制
# ==========================================

# 顶部标题 (只渲染一次)
if st.session_state.phase != 'solver':
    # 只要不是solver阶段，显示全局状态栏
    pl = st.session_state.player
    c1, c2, c3, c4 = st.columns(4)
    c1.markdown(f"<div class='stat-box'>📅 Day {pl['day']}</div>", unsafe_allow_html=True)
    c2.markdown(f"<div class='stat-box'>💰 机时 {pl['credits']}</div>", unsafe_allow_html=True)
    c3.markdown(f"<div class='stat-box'>🧠 SAN {pl['sanity']}</div>", unsafe_allow_html=True)
    c4.markdown(f"<div class='stat-box'>👴 发量 {pl['hair']}%</div>", unsafe_allow_html=True)
    st.markdown("---")

# --- 阶段分发 ---

if st.session_state.phase == 'home':
    st.title("⚡ CFD 极速模拟器")
    st.markdown("""
    <div class='scenario-text'>
    这是使用了 Streamlit Fragment 技术的极速版本。<br>
    求解器阶段不再全页刷新，操作零延迟。<br><br>
    目标：在博士毕业前发出一篇 SCI。
    </div>
    """, unsafe_allow_html=True)
    if st.button("👉 开始干活"):
        change_phase('project_select')

elif st.session_state.phase == 'project_select':
    st.subheader("选择课题")
    c1, c2, c3 = st.columns(3)
    if c1.button("🟢 DTMB 5415"):
        st.session_state.project.update({'name': 'DTMB 5415', 'difficulty': 2})
        change_phase('config')
    if c2.button("🟡 KCS 货船"):
        st.session_state.project.update({'name': 'KCS 货船', 'difficulty': 5})
        change_phase('config')
    if c3.button("🔴 ONR 破损船"):
        st.session_state.project.update({'name': 'ONR 破损船', 'difficulty': 9})
        change_phase('config')

elif st.session_state.phase == 'config':
    st.subheader("配置物理模型")
    st.write("选择湍流模型与创新点：")

    # 简化流程：点按钮直接添加/移除
    c1, c2 = st.columns(2)
    if c1.button("➕ 添加重叠网格 (Overset)"):
        if "Overset" not in st.session_state.project['innovations']:
            st.session_state.project['innovations'].append("Overset")
            st.toast("已添加 Overset")

    if c2.button("➕ 添加 6-DOF"):
        if "6-DOF" not in st.session_state.project['innovations']:
            st.session_state.project['innovations'].append("6-DOF")
            st.toast("已添加 6-DOF")

    st.write(f"当前创新点: {st.session_state.project['innovations']}")
    st.markdown("---")

    if st.button("🚀 开始计算"):
        st.session_state.project['residuals'] = [-1.0]
        change_phase('solver')

elif st.session_state.phase == 'solver':
    # 这一步直接调用 Fragment 函数
    # 主程序在这里停止刷新，剩下的交互全在 solver_dashboard 内部闭环
    solver_dashboard()

elif st.session_state.phase == 'result':
    st.subheader("投稿结果")
    p = st.session_state.project
    quality = p['difficulty'] * 10 + len(p['innovations']) * 20
    if p['residuals'][-1] > -3: quality -= 40

    st.markdown(f"<div class='scenario-text'>论文质量评分: {quality}</div>", unsafe_allow_html=True)

    if st.button("投递顶刊"):
        if quality > 70:
            st.balloons()
            st.success("Accepted! 导师很高兴。")
            update_stat('citations', quality)
        else:
            st.error("Rejected! 审稿人建议转投。")
            update_stat('sanity', -20)

    if st.button("🔄 下一个项目"):
        st.session_state.project['progress'] = 0
        st.session_state.project['residuals'] = []
        st.session_state.project['innovations'] = []
        change_phase('home')