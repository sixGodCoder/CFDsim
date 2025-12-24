import streamlit as st
import random
import time
import plotly.graph_objects as go

# ==========================================
# 1. 基础配置与样式
# ==========================================
st.set_page_config(page_title="CFD 学术大亨 V6.0", page_icon="🎓", layout="centered")

st.markdown("""
<style>
    /* 全局字体优化 */
    .main { font-family: "Microsoft YaHei", sans-serif; }
    
    /* 按钮样式 */
    .stButton>button {
        width: 100%;
        height: 55px;
        font-weight: bold;
        border-radius: 10px;
        border: 1px solid #ddd;
        transition: all 0.2s;
    }
    .stButton>button:hover {
        border-color: #00ADB5;
        color: #00ADB5;
        background-color: #f0faff;
    }
    
    /* 状态栏卡片 */
    .stat-card {
        background-color: #ffffff;
        padding: 10px;
        border-radius: 8px;
        box-shadow: 0 2px 5px rgba(0,0,0,0.05);
        text-align: center;
        border-top: 3px solid #00ADB5;
    }
    .stat-value { font-size: 18px; font-weight: bold; color: #333; }
    .stat-label { font-size: 12px; color: #666; }
    
    /* 剧情文本框 (浅色背景修复版) */
    .scenario-box {
        background-color: #f8f9fa;
        border-left: 5px solid #FF6B6B;
        padding: 15px;
        border-radius: 5px;
        margin-bottom: 20px;
        color: #2c3e50;
        font-size: 16px;
    }
    
    /* 商品卡片 */
    .shop-item {
        border: 1px solid #eee;
        padding: 10px;
        border-radius: 8px;
        margin-bottom: 10px;
        background: white;
    }
</style>
""", unsafe_allow_html=True)

# ==========================================
# 2. 游戏数据与状态初始化
# ==========================================

# 装备列表
SHOP_ITEMS = {
    "RTX 4090": {"price": 1500, "effect": "speed", "val": 1.5, "desc": "计算速度 +50%"},
    "UPS 不间断电源": {"price": 800, "effect": "safety", "val": 0.1, "desc": "崩溃概率 -10%"},
    "GitHub Copilot": {"price": 500, "effect": "sanity_save", "val": 2, "desc": "写代码 SAN 值消耗减半"},
    "Nature 编辑的邮箱": {"price": 5000, "effect": "luck", "val": 20, "desc": "中稿率大幅提升"},
}

if 'init' not in st.session_state:
    st.session_state.init = True
    st.session_state.phase = 'home' 
    
    # 玩家属性
    st.session_state.player = {
        'day': 1,
        'max_days': 1095, # 3年
        'funds': 3000,    # 经费 (钱)
        'sanity': 100,    # 理智
        'citations': 0,   # 引用 (分数)
        'inventory': [],  # 已买装备
        'speed_mult': 1.0, # 速度倍率
        'fail_rate': 0.0   # 降低炸机率
    }
    
    # 当前项目
    st.session_state.project = {
        'name': '',
        'difficulty': 0,
        'progress': 0,
        'residuals': [],
        'is_diverged': False,
        'event_active': False, # 是否触发了随机事件
        'event_msg': ''
    }

# ==========================================
# 3. 核心逻辑
# ==========================================

def update_player_stats():
    # 根据装备重新计算属性
    p = st.session_state.player
    p['speed_mult'] = 1.0
    p['fail_rate'] = 0.0
    
    if "RTX 4090" in p['inventory']: p['speed_mult'] += 0.5
    if "UPS 不间断电源" in p['inventory']: p['fail_rate'] -= 0.1

def trigger_random_event():
    events = [
        {"msg": "License 服务器连接超时！", "damage": "sanity", "val": -10, "choice": "重启路由器"},
        {"msg": "空调坏了，机房温度飙升！", "damage": "funds", "val": -200, "choice": "买冰块降温"},
        {"msg": "师弟把网格文件删了！", "damage": "progress", "val": -20, "choice": "从备份恢复"},
        {"msg": "发现官方文档里的公式印错了！", "damage": "sanity", "val": -15, "choice": "痛骂软件商"}
    ]
    if random.random() < 0.15: # 15% 概率触发
        evt = random.choice(events)
        st.session_state.project['event_active'] = True
        st.session_state.project['event_msg'] = evt
        return True
    return False

def run_solver_logic(mode):
    p = st.session_state.project
    pl = st.session_state.player
    
    # 策略参数
    settings = {
        'safe': {'cfl': 0.5, 'spd': 2, 'risk': 0.0, 'cost': 10},
        'normal': {'cfl': 1.0, 'spd': 5, 'risk': 0.05, 'cost': 5},
        'risky': {'cfl': 5.0, 'spd': 15, 'risk': 0.2, 'cost': 0}
    }
    s = settings[mode]
    
    # 扣费 (机时费)
    pl['funds'] -= s['cost']
    pl['day'] += 1
    
    # 随机事件检查 (优先级最高)
    if trigger_random_event():
        return "event_triggered"

    # 计算炸机概率 (基础风险 + 难度 - 装备保护)
    final_risk = s['risk'] + (p['difficulty'] / 100.0) + pl['fail_rate']
    if random.random() < final_risk:
        p['is_diverged'] = True
        p['residuals'].append(5.0)
        pl['sanity'] -= 10
        return "diverged"

    # 正常推进
    actual_speed = s['spd'] * pl['speed_mult']
    p['progress'] += actual_speed
    
    # 残差模拟
    last = p['residuals'][-1] if p['residuals'] else -0.5
    noise = random.uniform(-0.2, 0.2) * s['cfl']
    trend = -0.1 if s['cfl'] < 2 else -0.02
    new_res = max(-7, last + trend + noise)
    p['residuals'].append(new_res)
    
    if p['progress'] >= 100:
        return "done"
    return "running"

# ==========================================
# 4. 界面组件 (Fragments)
# ==========================================

# 顶部状态栏
def render_header():
    pl = st.session_state.player
    c1, c2, c3, c4 = st.columns(4)
    c1.markdown(f"<div class='stat-card'><div class='stat-value'>{pl['day']}/{pl['max_days']}</div><div class='stat-label'>倒计时 (天)</div></div>", unsafe_allow_html=True)
    c2.markdown(f"<div class='stat-card'><div class='stat-value'>¥{pl['funds']}</div><div class='stat-label'>科研经费</div></div>", unsafe_allow_html=True)
    c3.markdown(f"<div class='stat-card'><div class='stat-value'>{pl['sanity']}</div><div class='stat-label'>SAN值</div></div>", unsafe_allow_html=True)
    c4.markdown(f"<div class='stat-card'><div class='stat-value'>{pl['citations']}</div><div class='stat-label'>学术引用</div></div>", unsafe_allow_html=True)
    st.markdown("---")

# 求解器面板 (局部刷新)
@st.fragment
def solver_panel():
    p = st.session_state.project
    
    # 1. 绘图
    if p['residuals']:
        fig = go.Figure()
        fig.add_trace(go.Scatter(y=p['residuals'], mode='lines', line=dict(color='#00ADB5', width=2)))
        fig.update_layout(height=250, margin=dict(t=10,b=10,l=10,r=10), 
                         template='plotly_white', xaxis_title="Iterations", yaxis_title="Log Residual")
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("💡 准备就绪。请选择策略开始迭代。")

    # 2. 状态处理
    if p['event_active']:
        evt = p['event_msg']
        st.markdown(f"<div class='scenario-box'>⚡ 突发事件：{evt['msg']}</div>", unsafe_allow_html=True)
        if st.button(f"😭 {evt['choice']} ({evt['damage']} {evt['val']})"):
            # 结算事件伤害
            if evt['damage'] == 'funds': st.session_state.player['funds'] += evt['val']
            if evt['damage'] == 'sanity': st.session_state.player['sanity'] += evt['val']
            if evt['damage'] == 'progress': p['progress'] = max(0, p['progress'] + evt['val'])
            p['event_active'] = False
            st.rerun()

    elif p['is_diverged']:
        st.error("💥 残差发散！计算崩溃了。")
        c1, c2 = st.columns(2)
        if c1.button("🛠️ 紧急修复 (花费 ¥200)"):
            if st.session_state.player['funds'] >= 200:
                st.session_state.player['funds'] -= 200
                p['is_diverged'] = False
                p['residuals'].append(p['residuals'][-1] - 2)
                st.rerun()
            else:
                st.toast("没钱修复！")
        if c2.button("💀 放弃重开"):
            p['residuals'] = []
            p['progress'] = 0
            p['is_diverged'] = False
            st.session_state.phase = 'lobby'
            st.rerun()

    elif p['progress'] >= 100:
        st.success("✅ 计算完成！")
        if st.button("📄 整理数据去发论文"):
            st.session_state.phase = 'result'
            st.rerun()

    else:
        # 正常操作区
        c1, c2, c3 = st.columns(3)
        with c1:
            if st.button("🛡️ 稳健迭代\nCFL 0.5 | ¥10"):
                run_solver_logic('safe')
                st.rerun()
        with c2:
            if st.button("⚖️ 标准迭代\nCFL 1.0 | ¥5"):
                run_solver_logic('normal')
                st.rerun()
        with c3:
            if st.button("🔥 激进迭代\nCFL 5.0 | 免费"):
                run_solver_logic('risky')
                st.rerun()

# ==========================================
# 5. 主流程控制
# ==========================================

render_header()

# --- 游戏结束判断 ---
if st.session_state.player['day'] >= 1095:
    st.error("⏳ 3年非升即走考核期满！")
    if st.session_state.player['citations'] >= 1000:
        st.balloons()
        st.markdown("# 🎉 恭喜！你获得了终身教职 (Tenure)！")
        st.markdown("你成为了学术界的大佬，从此以后可以尽情压榨学生了（误）。")
    else:
        st.markdown("# 😭 考核失败")
        st.markdown(f"你只获得了 {st.session_state.player['citations']} 引用，距离目标还差 {1000 - st.session_state.player['citations']}。")
        st.markdown("你被迫转行去送外卖了。")
    if st.button("🔄 重新开始人生"):
        st.session_state.clear()
        st.rerun()
    st.stop()

if st.session_state.player['funds'] < 0:
    st.error("💸 经费耗尽，项目组破产解散！")
    if st.button("🔄 重新开始"):
        st.session_state.clear()
        st.rerun()
    st.stop()

# --- 阶段分发 ---

if st.session_state.phase == 'home':
    st.title("🎓 CFD 学术大亨")
    st.markdown("""
    <div class='scenario-box'>
    <b>目标：</b>在 3 年 (1095天) 内获得 1000 次引用。<br>
    <b>资源：</b>管理你的经费、SAN值和计算资源。<br>
    <b>警告：</b>小心发散，小心审稿人。
    </div>
    """, unsafe_allow_html=True)
    if st.button("🚀 开始学术生涯"):
        st.session_state.phase = 'lobby'
        st.rerun()

elif st.session_state.phase == 'lobby':
    st.subheader("🏫 实验室大厅")
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.write("#### 📂 接新项目")
        st.info("完成项目可获得经费和引用。")
        c1, c2, c3 = st.columns(3)
        if c1.button("🟢 圆柱绕流\n难度: 低 | 收益: 低"):
            st.session_state.project.update({'name': '圆柱绕流', 'difficulty': 10, 'reward_funds': 1000})
            st.session_state.phase = 'solver'
            st.rerun()
        if c2.button("🟡 KCS 船模\n难度: 中 | 收益: 中"):
            st.session_state.project.update({'name': 'KCS 船模', 'difficulty': 30, 'reward_funds': 2500})
            st.session_state.phase = 'solver'
            st.rerun()
        if c3.button("🔴 实船破舱\n难度: 高 | 收益: 高"):
            st.session_state.project.update({'name': '实船破舱', 'difficulty': 60, 'reward_funds': 6000})
            st.session_state.phase = 'solver'
            st.rerun()

    with col2:
        st.write("#### 🛒 采购设备")
        for name, item in SHOP_ITEMS.items():
            disabled = name in st.session_state.player['inventory']
            btn_label = "✅ 已拥有" if disabled else f"¥{item['price']} 购买"
            
            with st.container(border=True):
                st.write(f"**{name}**")
                st.caption(item['desc'])
                if st.button(btn_label, key=name, disabled=disabled):
                    if st.session_state.player['funds'] >= item['price']:
                        st.session_state.player['funds'] -= item['price']
                        st.session_state.player['inventory'].append(name)
                        update_player_stats()
                        st.toast(f"成功购买 {name}!")
                        st.rerun()
                    else:
                        st.toast("经费不足！")

elif st.session_state.phase == 'solver':
    st.subheader(f"正在计算：{st.session_state.project['name']}")
    solver_panel()

elif st.session_state.phase == 'result':
    p = st.session_state.project
    pl = st.session_state.player
    
    st.subheader("📧 投稿结果反馈")
    
    # 结算逻辑
    base_score = random.randint(50, 100)
    if "Nature 编辑的邮箱" in pl['inventory']: base_score += 20
    
    quality = base_score - (p['residuals'][-1] * 5) # 残差越小分越高
    
    st.markdown(f"<div class='scenario-box'>论文质量评分: {int(quality)}</div>", unsafe_allow_html=True)
    
    col1, col2 = st.columns(2)
    with col1:
        if st.button("投递顶刊 (JFM/JCP)"):
            if quality > 85:
                st.balloons()
                reward_cite = random.randint(50, 150)
                pl['citations'] += reward_cite
                pl['funds'] += p['reward_funds']
                st.success(f"录用！获得 {reward_cite} 引用，结题经费 ¥{p['reward_funds']}")
            else:
                st.error("拒稿！评审意见：创新点不足。")
                pl['sanity'] -= 20
            
            # 无论成功失败，都回大厅
            if st.button("🔙 返回大厅"):
                st.session_state.project['progress'] = 0
                st.session_state.project['residuals'] = []
                st.session_state.project['is_diverged'] = False
                st.session_state.phase = 'lobby'
                st.rerun()
                
    with col2:
        if st.button("投递水刊 (OA期刊)"):
            reward_cite = random.randint(5, 20)
            pl['citations'] += reward_cite
            pl['funds'] += int(p['reward_funds'] * 0.5) # 水刊结题评价低
            st.success(f"录用 (虽然要交版面费)。获得 {reward_cite} 引用，经费 ¥{int(p['reward_funds']*0.5)}")
            
            if st.button("🔙 返回大厅"):
                st.session_state.project['progress'] = 0
                st.session_state.project['residuals'] = []
                st.session_state.project['is_diverged'] = False
                st.session_state.phase = 'lobby'
                st.rerun()
