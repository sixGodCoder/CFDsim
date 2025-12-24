import streamlit as st
import random
import time
import pandas as pd
import numpy as np
import plotly.graph_objects as go

# ==========================================
# 0. 移动端优先配置与CSS
# ==========================================
st.set_page_config(page_title="CFD 口袋大亨 V8.0", page_icon="📱", layout="centered")

st.markdown("""
<style>
    /* 全局字体与背景 */
    .main { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; }
    
    /* 移动端卡片样式 */
    .mobile-card {
        background: #ffffff;
        padding: 15px;
        border-radius: 10px;
        box-shadow: 0 2px 8px rgba(0,0,0,0.08);
        border-top: 4px solid #00ADB5;
        margin-bottom: 15px;
    }
    
    /* 大按钮优化 (适合手指点击) */
    .stButton>button {
        width: 100%;
        height: 50px; /* 增大高度 */
        font-size: 16px !important;
        font-weight: 600;
        border-radius: 8px;
        margin-top: 5px;
    }
    
    /* 关键数值高亮 */
    .highlight-val { font-size: 20px; font-weight: bold; color: #2C3E50; }
    .highlight-label { font-size: 12px; color: #7F8C8D; }
    
    /* 求解器控制台 - 手机版高度减小 */
    .solver-log {
        background: #1e1e1e;
        color: #00ff00;
        font-family: monospace;
        font-size: 12px;
        padding: 8px;
        border-radius: 5px;
        height: 100px;
        overflow-y: scroll;
    }
</style>
""", unsafe_allow_html=True)

# ==========================================
# 1. 状态初始化
# ==========================================
if 'init' not in st.session_state:
    st.session_state.init = True
    
    # 玩家属性
    st.session_state.player = {
        'day': 1,
        'funds': 20000,
        'energy': 100,
        'reputation': 0,
        'inventory_data': []
    }
    
    # 求解器状态 (增强版)
    st.session_state.solver = {
        'progress': 0,
        'residuals': [-1.0],
        'cfl': 1.0,
        'urf': 0.7,
        'mesh_quality': 50, # 新属性：网格质量 (0-100)
        'diverged': False,
        'auto_run': False,  # 自动托管状态
        'logs': ["System Ready."]
    }

# 工具函数：添加日志
def log_msg(msg):
    st.session_state.solver['logs'].insert(0, f"[{st.session_state.player['day']}] {msg}")

# ==========================================
# PAGE 1: 🏢 实验室 (Lab) - 移动端精简版
# ==========================================
def page_lab():
    pl = st.session_state.player
    st.markdown("### 🏢 移动实验室")
    
    # 顶部资源栏 (2x2 布局)
    c1, c2 = st.columns(2)
    c1.markdown(f"<div class='mobile-card'><div class='highlight-val'>¥{pl['funds']}</div><div class='highlight-label'>科研经费</div></div>", unsafe_allow_html=True)
    c2.markdown(f"<div class='mobile-card'><div class='highlight-val'>{pl['energy']}/100</div><div class='highlight-label'>导师精力</div></div>", unsafe_allow_html=True)
    
    # 选项卡式管理
    tab1, tab2 = st.tabs(["👥 团队管理", "🛠️ 资源采购"])
    
    with tab1:
        st.info("点击按钮消耗精力督促学生干活。")
        if st.button("👨‍🎓 督促硕士生 (精力-5)"):
            if pl['energy'] >= 5:
                pl['energy'] -= 5
                gain = random.randint(500, 1500)
                pl['funds'] += gain
                st.toast(f"学生接了个横向项目，经费 +{gain}")
            else:
                st.error("精力不足，去喝咖啡！")
                
        if st.button("☕ 喝冰美式 (经费-50)"):
            if pl['funds'] >= 50:
                pl['funds'] -= 50
                pl['energy'] = min(100, pl['energy'] + 30)
                st.toast("精神焕发！")

    with tab2:
        st.write("购买云算力加速求解：")
        if st.button("☁️ 租用阿里云节点 (¥2000)"):
            if pl['funds'] >= 2000:
                pl['funds'] -= 2000
                st.session_state.solver['mesh_quality'] += 10 # 更好的硬件能跑更好的网格
                st.success("算力升级！网格承载力提升。")
            else: st.error("缺钱")

# ==========================================
# PAGE 2: ⚡ 求解器驾驶舱 (Solver Cockpit)
# ==========================================
@st.fragment
def page_solver():
    sv = st.session_state.solver
    pl = st.session_state.player
    
    st.markdown("### ⚡ 求解器驾驶舱")
    
    # 1. HUD 抬头显示 (关键状态)
    # 计算当前崩溃风险
    risk = (sv['cfl'] * 2) * (1.1 - sv['urf']) * (100 - sv['mesh_quality']) * 0.001
    risk = min(0.99, max(0.01, risk))
    risk_color = "red" if risk > 0.3 else "green"
    
    col1, col2, col3 = st.columns(3)
    col1.metric("进度", f"{int(sv['progress'])}%")
    col2.metric("网格质量", sv['mesh_quality'])
    col3.metric("崩溃风险", f"{int(risk*100)}%")
    
    # 2. 核心图表 (高度适应手机)
    if sv['residuals']:
        fig = go.Figure()
        fig.add_trace(go.Scatter(y=sv['residuals'], mode='lines', line=dict(color='#00ADB5', width=3)))
        fig.update_layout(
            margin=dict(l=10, r=10, t=10, b=10),
            height=250, # 手机上不要太高
            template="plotly_dark",
            yaxis_title="Log Res",
            xaxis_visible=False
        )
        st.plotly_chart(fig, use_container_width=True)
    
    # 3. 控制面板 (功能区)
    
    # A区：参数调节 (Sliders)
    with st.expander("🎛️ 参数设置 (CFL / URF)", expanded=True):
        sv['cfl'] = st.slider("CFL (速度)", 0.1, 5.0, sv['cfl'], 0.1)
        sv['urf'] = st.slider("URF (稳定)", 0.1, 1.0, sv['urf'], 0.1)

    # B区：主动技能 (Buttons) - 核心玩法更新
    st.write("**🕹️ 操作指令**")
    
    # 状态处理
    if sv['diverged']:
        st.error("💥 计算发散 (Diverged)！")
        if st.button("🔄 重置求解器 (Reset)"):
            sv['residuals'] = [-1.0]
            sv['progress'] = 0
            sv['diverged'] = False
            sv['auto_run'] = False
            log_msg("Solver reset.")
            st.rerun()
            
    elif sv['progress'] >= 100:
        st.success("✅ 计算完成！")
        if st.button("💾 提取结果数据"):
            pl['inventory_data'].append({'quality': sv['mesh_quality'] + random.randint(0, 20)})
            sv['progress'] = 0
            sv['residuals'] = [-1.0]
            sv['auto_run'] = False
            st.toast("数据已保存！")
            st.rerun()
    else:
        # 正常操作按钮矩阵
        b_col1, b_col2 = st.columns(2)
        
        with b_col1:
            # 技能 1: 单步运行
            if st.button("▶️ 单步迭代"):
                do_solve_step(1, risk)
                st.rerun()
            
            # 技能 3: AMR 自适应网格 (花钱消灾)
            if st.button("🛠️ AMR 加密网格\n(¥500)"):
                if pl['funds'] >= 500:
                    pl['funds'] -= 500
                    sv['mesh_quality'] = min(100, sv['mesh_quality'] + 5)
                    log_msg("Applied AMR. Mesh quality +5")
                    st.rerun()
                else: st.toast("经费不足")

        with b_col2:
            # 技能 2: 自动托管 (风险)
            if st.button("🤖 自动托管 10步"):
                for _ in range(10):
                    time.sleep(0.05) # 视觉延迟
                    res = do_solve_step(1, risk)
                    if res == "stop": break
                st.rerun()
            
            # 技能 4: 强效稳像 (救火)
            if st.button("💊 注入镇静剂\n(精力-10)"):
                if pl['energy'] >= 10:
                    pl['energy'] -= 10
                    sv['residuals'].append(sv['residuals'][-1] - 1.5) # 强行压残差
                    sv['urf'] = max(0.1, sv['urf'] - 0.2) # 自动降松弛
                    log_msg("Stabilizer injected!")
                    st.rerun()
                else: st.toast("精力不足")

    # 4. 日志区
    st.markdown(f"<div class='solver-log'>{sv['logs'][0]}<br>{sv['logs'][1] if len(sv['logs'])>1 else ''}</div>", unsafe_allow_html=True)

def do_solve_step(steps, risk):
    sv = st.session_state.solver
    
    # 判定发散
    if random.random() < risk:
        sv['diverged'] = True
        sv['residuals'].append(5.0)
        log_msg("ERROR: Divergence detected!")
        return "stop"
    
    # 正常计算
    sv['progress'] += (sv['cfl'] * 2.0)
    
    # 残差计算
    last_res = sv['residuals'][-1]
    # 网格质量越好，残差越容易下降
    quality_factor = (sv['mesh_quality'] - 50) * 0.005
    drop = -0.1 * sv['urf'] - quality_factor
    noise = random.uniform(-0.5, 0.5) * sv['cfl'] * 0.1
    new_res = max(-8, last_res + drop + noise)
    
    sv['residuals'].append(new_res)
    return "ok"

# ==========================================
# PAGE 3: 📝 论文与答辩 (Paper)
# ==========================================
def page_paper():
    st.markdown("### 📝 论文投稿")
    pl = st.session_state.player
    
    if not pl['inventory_data']:
        st.info("暂无实验数据，请去【求解器】计算。")
        return

    # 简化版合成逻辑
    data = pl['inventory_data'][-1] # 取最新的数据
    st.write(f"最新数据质量: **{data['quality']}**")
    
    if st.button("📤 撰写并投递 JFM"):
        score = data['quality']
        pl['inventory_data'].pop() # 消耗数据
        
        st.write("---")
        st.write("Reviewer #2 正在审稿...")
        progress_bar = st.progress(0)
        for i in range(100):
            time.sleep(0.01)
            progress_bar.progress(i+1)
            
        # 简单判定
        if score > 80:
            st.balloons()
            st.success("🎉 ACCEPTED! 恭喜录用！")
            pl['reputation'] += 100
            pl['funds'] += 5000
        else:
            st.error("😭 REJECTED! 数据质量太差。")
            pl['energy'] -= 20

# ==========================================
# 主导航逻辑 (移动端底部导航栏模拟)
# ==========================================

# 使用 sidebar 在手机上会折叠，也可以用 st.radio 横向排列模拟底部导航
# 这里为了手机体验，我们用 radio 放在顶部，或者用 expander
st.sidebar.title("CFD Tycoon 📱")
page = st.sidebar.radio("菜单", ["🏢 实验室", "⚡ 求解器", "📝 论文投稿"])

if page == "🏢 实验室":
    page_lab()
elif page == "⚡ 求解器":
    page_solver()
elif page == "📝 论文投稿":
    page_paper()

# 底部全局状态简报 (方便随时看钱)
st.sidebar.markdown("---")
st.sidebar.caption(f"Day: {st.session_state.player['day']} | Funds: ¥{st.session_state.player['funds']}")
