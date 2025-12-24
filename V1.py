import streamlit as st
import random
import time
import pandas as pd
import numpy as np
import plotly.graph_objects as go

# ==========================================
# 1. 基础配置
# ==========================================
st.set_page_config(page_title="CFD 模拟器: 按钮版", page_icon="🚢", layout="centered")

# CSS 美化：让按钮看起来像游戏选项卡
st.markdown("""
<style>
    .stButton>button {
        width: 100%;
        height: 60px;
        font-size: 18px !important;
        font-weight: bold;
        border-radius: 12px;
        border: 2px solid #333;
        transition: all 0.2s;
    }
    .stButton>button:hover {
        transform: scale(1.02);
        border-color: #00ADB5;
    }
    .stat-box {
        background: #222;
        padding: 10px;
        border-radius: 8px;
        text-align: center;
        border: 1px solid #444;
        margin-bottom: 10px;
    }
    .scenario-text {
        font-size: 20px;
        line-height: 1.6;
        margin-bottom: 30px;
        padding: 20px;
        background: #1E1E1E;
        border-left: 5px solid #00ADB5;
        border-radius: 5px;
    }
</style>
""", unsafe_allow_html=True)

# ==========================================
# 2. 状态初始化
# ==========================================
if 'init' not in st.session_state:
    st.session_state.init = True
    st.session_state.phase = 'home' # home, project_select, config, solver, result
    st.session_state.logs = []
    
    # 玩家属性
    st.session_state.player = {
        'day': 1,
        'hair': 100,
        'sanity': 100,
        'credits': 500, # HPC机时
        'citations': 0
    }
    
    # 当前项目暂存
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
# 3. 辅助逻辑
# ==========================================

def change_phase(new_phase):
    st.session_state.phase = new_phase
    st.rerun()

def update_stat(key, value):
    st.session_state.player[key] += value

def run_solver_step(mode):
    p = st.session_state.project
    
    # 模式定义
    if mode == 'safe':
        cfl = 0.5
        speed = 2
        risk = 0.0
        cost = 20
    elif mode == 'normal':
        cfl = 1.0
        speed = 5
        risk = 0.05
        cost = 10
    elif mode == 'risky':
        cfl = 5.0
        speed = 15
        risk = 0.25 + (p['difficulty'] / 50.0) # 难度越高炸率越高
        cost = 5

    # 扣费
    if st.session_state.player['credits'] < cost:
        return "no_money"
    st.session_state.player['credits'] -= cost
    st.session_state.player['day'] += 1

    # 判定发散
    # 创新点越多，越容易炸
    innovation_penalty = len(p['innovations']) * 0.05
    final_risk = risk + innovation_penalty
    
    if random.random() < final_risk:
        p['is_diverged'] = True
        p['diverge_reason'] = random.choice([
            "Negative Volume (网格负体积)",
            "SIGSEGV (段错误)",
            "Divergence in AMG Solver",
            "Floating Point Exception"
        ])
        p['residuals'].append(5.0)
        update_stat('sanity', -10)
        update_stat('hair', -5)
        return "diverged"

    # 正常计算
    p['progress'] += speed
    
    # 残差模拟
    last_res = p['residuals'][-1] if p['residuals'] else -1.0
    # 残差波动逻辑
    base_drop = -0.1 if cfl < 2 else -0.05
    noise = random.uniform(-0.2, 0.2) * cfl
    new_res = last_res + base_drop + noise
    new_res = max(-6, new_res) # 下限 -6
    p['residuals'].append(new_res)
    
    if p['progress'] >= 100:
        return "done"
    return "running"

# ==========================================
# 4. 界面渲染 (分阶段)
# ==========================================

# 顶部状态栏 (永远显示)
pl = st.session_state.player
c1, c2, c3, c4 = st.columns(4)
c1.markdown(f"<div class='stat-box'>📅 Day {pl['day']}</div>", unsafe_allow_html=True)
c2.markdown(f"<div class='stat-box'>💰 机时 {pl['credits']}</div>", unsafe_allow_html=True)
c3.markdown(f"<div class='stat-box'>🧠 SAN {pl['sanity']}</div>", unsafe_allow_html=True)
c4.markdown(f"<div class='stat-box'>👴 发量 {pl['hair']}%</div>", unsafe_allow_html=True)

st.markdown("---")

# --- 阶段 0: 首页 ---
if st.session_state.phase == 'home':
    st.title("🚢 CFD 仿真模拟器")
    st.markdown("""
    <div class='scenario-text'>
    你是一名刚刚入学的流体力学博士生。<br>
    导师把你叫到办公室，指着屏幕上的 STAR-CCM+ 图标说：<br>
    “今年必须要发一篇顶刊，否则不用毕业了。”
    </div>
    """, unsafe_allow_html=True)
    
    if st.button("👉 开始干活 (Start)"):
        change_phase('project_select')

# --- 阶段 1: 选题 (三选一) ---
elif st.session_state.phase == 'project_select':
    st.subheader("第一步：选择研究课题")
    st.write("导师给了你三个可选的船型方向，请做出选择：")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("🟢 DTMB 5415\n(静水阻力)"):
            st.session_state.project['name'] = "DTMB 5415 阻力"
            st.session_state.project['difficulty'] = 2
            change_phase('config')
            
    with col2:
        if st.button("🟡 KCS 货船\n(波浪增阻)"):
            st.session_state.project['name'] = "KCS 波浪增阻"
            st.session_state.project['difficulty'] = 5
            change_phase('config')
            
    with col3:
        if st.button("🔴 ONR Tumblehome\n(破损自航)"):
            st.session_state.project['name'] = "ONR 破损自航"
            st.session_state.project['difficulty'] = 9
            change_phase('config')
            
    st.info("提示：难度越高，发顶刊概率越大，但计算越容易报错。")

# --- 阶段 2: 物理配置 (按钮阵列) ---
elif st.session_state.phase == 'config':
    st.subheader("第二步：配置物理模型")
    st.write(f"当前项目: **{st.session_state.project['name']}**")
    st.write("你需要确定求解策略。越花哨的方法，审稿人越喜欢，但也越烧钱。")
    
    st.markdown("### 1. 湍流模型 (Turbulence)")
    c1, c2 = st.columns(2)
    with c1:
        if st.button("RANS (k-epsilon)\n稳定、便宜、老旧"):
            st.session_state.project['method'] = "RANS"
            # 这里的逻辑稍微改一下，直接进入下一环节，或者存状态
            # 为了简化按钮流，我们选完这个直接去选创新点
    with c2:
        if st.button("DES / LES (大涡模拟)\n高精度、昂贵、易发散"):
            st.session_state.project['method'] = "LES"
            st.session_state.project['difficulty'] += 5 # 难度激增
    
    # 如果用户没点上面的，下面的代码不会执行，因为rerun。
    # 为了实现 sequential flow，必须把 state 存下来。
    # 这里为了演示方便，做一个简单判定：如果 project['method'] 还是空，就只显示上面。
    # 如果选了 method，就显示下一步。
    
    if st.session_state.project['method'] != '':
        st.markdown("### 2. 添加创新点 (Buff)")
        st.info("点击添加，增加论文含金量：")
        
        col_i1, col_i2, col_i3 = st.columns(3)
        
        # 使用 toggle 逻辑：检查是否在列表里
        has_overset = "重叠网格" in st.session_state.project['innovations']
        label_overset = "✅ 已添加: 重叠网格" if has_overset else "➕ 重叠网格 (Overset)"
        if col_i1.button(label_overset):
            if has_overset: st.session_state.project['innovations'].remove("重叠网格")
            else: st.session_state.project['innovations'].append("重叠网格")
            st.rerun()

        has_vof = "高阶VOF格式" in st.session_state.project['innovations']
        label_vof = "✅ 已添加: 高阶VOF" if has_vof else "➕ 高阶VOF格式"
        if col_i2.button(label_vof):
            if has_vof: st.session_state.project['innovations'].remove("高阶VOF格式")
            else: st.session_state.project['innovations'].append("高阶VOF格式")
            st.rerun()
            
        has_6dof = "6自由度运动" in st.session_state.project['innovations']
        label_6dof = "✅ 已添加: 6-DOF" if has_6dof else "➕ 6自由度运动"
        if col_i3.button(label_6dof):
            if has_6dof: st.session_state.project['innovations'].remove("6自由度运动")
            else: st.session_state.project['innovations'].append("6自由度运动")
            st.rerun()

        st.markdown("---")
        if st.button("🚀 配置完成，生成网格并开始计算！"):
            # 初始化残差
            st.session_state.project['residuals'] = [-1.0]
            change_phase('solver')

# --- 阶段 3: 求解器 (核心玩法) ---
elif st.session_state.phase == 'solver':
    p = st.session_state.project
    
    st.subheader("第三步：计算求解 (Solver)")
    
    # 1. 绘图区域
    if p['residuals']:
        fig = go.Figure()
        fig.add_trace(go.Scatter(y=p['residuals'], mode='lines', name='Residual', line=dict(color='#00ADB5', width=3)))
        fig.update_layout(
            title=f"残差监视器 (Progress: {p['progress']}%)",
            xaxis_title="Iterations",
            yaxis_title="Log(Residuals)",
            template="plotly_dark",
            height=300,
            yaxis_range=[-7, 10]
        )
        st.plotly_chart(fig, use_container_width=True)
    
    # 2. 状态判定
    if p['is_diverged']:
        st.error(f"❌ 计算发散！错误代码: {p['diverge_reason']}")
        st.markdown("""
        <div class='scenario-text'>
        屏幕上弹出了红色的错误窗口，你的心情跌落谷底。<br>
        现在你有两个选择：
        </div>
        """, unsafe_allow_html=True)
        
        c1, c2 = st.columns(2)
        with c1:
            if st.button("🛠️ 减小松弛因子救一下 (SAN -10)"):
                p['is_diverged'] = False
                p['residuals'].append(p['residuals'][-1] - 3) # 强行压下去
                update_stat('sanity', -10)
                st.rerun()
        with c2:
            if st.button("💥 彻底放弃，重开项目"):
                st.session_state.project['residuals'] = []
                st.session_state.project['progress'] = 0
                st.session_state.project['is_diverged'] = False
                change_phase('config')
                
    elif p['progress'] >= 100:
        st.success("✅ 计算收敛！")
        if st.button("📄 提取数据，撰写论文"):
            change_phase('result')
            
    else:
        # 3. 操作区域 (三个策略按钮)
        st.write("请选择下一步的迭代策略：")
        
        c1, c2, c3 = st.columns(3)
        
        with c1:
            if st.button("🛡️ 苟住 (Safe)\nCFL 0.5 | 慢速 | 极稳"):
                res = run_solver_step('safe')
                if res == "no_money": st.toast("没钱买机时了！")
                st.rerun()
                
        with c2:
            if st.button("⚖️ 稳健 (Normal)\nCFL 1.0 | 标准 | 微险"):
                res = run_solver_step('normal')
                if res == "no_money": st.toast("没钱买机时了！")
                st.rerun()
                
        with c3:
            if st.button("🔥 赌狗 (Risky)\nCFL 5.0 | 极速 | 易炸"):
                res = run_solver_step('risky')
                if res == "no_money": st.toast("没钱买机时了！")
                st.rerun()

# --- 阶段 4: 结果结算 ---
elif st.session_state.phase == 'result':
    p = st.session_state.project
    st.subheader("第四步：投稿环节")
    
    # 计算最终评分
    quality = p['difficulty'] * 10 + len(p['innovations']) * 20
    final_res = p['residuals'][-1]
    if final_res > -3: quality -= 30 # 收敛不好扣分
    if p['method'] == 'LES': quality += 30
    
    st.markdown(f"""
    <div class='scenario-text'>
    你完成了《{p['name']}》的模拟。<br>
    最终残差收敛至: 1e{int(final_res)}<br>
    论文质量评分: {quality}
    </div>
    """, unsafe_allow_html=True)
    
    st.write("请选择投稿目标：")
    
    c1, c2 = st.columns(2)
    with c1:
        if st.button("JFM / Ocean Eng. (顶刊)"):
            if quality > 80:
                st.balloons()
                st.success(f"恭喜！Reviewer 虽然提了 20 个意见，但最终接受了！引用 +{quality}")
                update_stat('citations', quality)
                update_stat('sanity', 20)
            else:
                st.error("拒稿！Reviewer #2 说你的网格无关性验证是伪造的。")
                update_stat('sanity', -20)
            
            if st.button("🔄 下一个项目"):
                st.session_state.project['name'] = '' # Reset
                st.session_state.project['progress'] = 0
                st.session_state.project['innovations'] = []
                st.session_state.project['residuals'] = []
                change_phase('home')

    with c2:
        if st.button("水刊 (Open Access)"):
            st.success("发表成功！虽然没什么人看，但至少能毕业。引用 +10")
            update_stat('citations', 10)
            
            if st.button("🔄 下一个项目"):
                st.session_state.project['name'] = '' # Reset
                st.session_state.project['progress'] = 0
                st.session_state.project['innovations'] = []
                st.session_state.project['residuals'] = []
                change_phase('home')

# 底部重置按钮
st.markdown("---")
if st.button("💀 删档重来 (Reset Game)"):
    st.session_state.clear()
    st.rerun()
