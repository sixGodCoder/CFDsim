import streamlit as st
import random
import time
import pandas as pd
import numpy as np
import plotly.graph_objects as go

# ==========================================
# 0. 全局配置与样式
# ==========================================
st.set_page_config(page_title="CFD 学术大亨 V7.0", page_icon="🎓", layout="wide")

st.markdown("""
<style>
    /* 全局样式 */
    .main { font-family: "Segoe UI", sans-serif; }
    
    /* 大卡片样式 */
    .game-card {
        background: #ffffff;
        padding: 20px;
        border-radius: 12px;
        box-shadow: 0 4px 15px rgba(0,0,0,0.05);
        border-left: 5px solid #00ADB5;
        margin-bottom: 20px;
    }
    
    /* 仪表盘数字 */
    .metric-value { font-size: 24px; font-weight: bold; color: #222; }
    .metric-label { font-size: 14px; color: #666; }
    
    /* 求解器控制台 */
    .solver-console {
        background: #000;
        color: #0f0;
        font-family: 'Consolas', monospace;
        padding: 10px;
        border-radius: 5px;
        height: 150px;
        overflow-y: auto;
    }
    
    /* 战斗血条 */
    .health-bar-bg { width: 100%; background: #ddd; height: 10px; border-radius: 5px; }
    .health-bar-fill { height: 100%; background: #ff4b4b; border-radius: 5px; transition: width 0.3s; }
</style>
""", unsafe_allow_html=True)

# ==========================================
# 1. 游戏状态初始化
# ==========================================
if 'init' not in st.session_state:
    st.session_state.init = True
    
    # 玩家全局属性
    st.session_state.player = {
        'day': 1,
        'funds': 50000,    # 启动资金
        'reputation': 0,   # 声望
        'energy': 100,     # 导师精力
        'students': [],    # 招募的学生
        'hardware': 'Laptop', # 硬件等级
        'inventory_data': [] # 算出来的结果数据
    }
    
    # 当前项目状态
    st.session_state.solver = {
        'running': False,
        'progress': 0,
        'residuals': [-1.0],
        'cfl': 1.0,        # 库朗数 (玩家控制)
        'urf': 0.7,        # 松弛因子 (玩家控制)
        'diverged': False,
        'logs': ["Ready to solve..."]
    }
    
    # 战斗状态
    st.session_state.battle = {
        'active': False,
        'reviewer_hp': 100,
        'player_hp': 100,
        'turn_log': []
    }

# 工具函数
def add_solver_log(msg):
    st.session_state.solver['logs'].insert(0, f"[{st.session_state.player['day']}] {msg}")

# ==========================================
# PAGE 1: 🏢 实验室运营 (Management)
# ==========================================
def page_lab():
    st.title("🏢 CFD 实验室运营中心")
    pl = st.session_state.player
    
    # 顶部资源栏
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("经费", f"¥{pl['funds']}")
    c2.metric("声望", pl['reputation'])
    c3.metric("精力", f"{pl['energy']}/100")
    c4.metric("硬件", pl['hardware'])
    
    col_left, col_right = st.columns([2, 1])
    
    with col_left:
        st.subheader("👥 人才管理")
        if not pl['students']:
            st.info("你的实验室空空如也。先招个牛马...啊不，研究生吧。")
        else:
            for i, stu in enumerate(pl['students']):
                with st.container(border=True):
                    sc1, sc2 = st.columns([3, 1])
                    sc1.write(f"🎓 **{stu['name']}** ({stu['type']})")
                    sc1.caption(f"能力: {stu['skill']} | 心情: {stu['mood']}")
                    if sc2.button("督促干活", key=f"work_{i}"):
                        pl['energy'] -= 5
                        stu['mood'] -= 10
                        st.toast(f"{stu['name']} 去画网格了，心情 -10")
        
        st.divider()
        st.subheader("🛠️ 硬件升级")
        hc1, hc2 = st.columns(2)
        if hc1.button("购买工作站 (¥20,000)"):
            if pl['funds'] >= 20000:
                pl['funds'] -= 20000
                pl['hardware'] = "Workstation"
                st.success("硬件升级！求解速度翻倍。")
                st.rerun()
            else: st.error("经费不足")
            
        if hc2.button("租用超算集群 (¥5,000/月)"):
            if pl['funds'] >= 5000:
                pl['funds'] -= 5000
                pl['hardware'] = "HPC Cluster"
                st.success("接入天河二号！速度起飞。")
                st.rerun()
            else: st.error("经费不足")

    with col_right:
        st.subheader("📋 招聘启事")
        with st.container(border=True):
            st.write("**硕士研究生**")
            st.caption("便宜，听话，但经常犯错。")
            if st.button("招募 (花费 ¥2000/月)"):
                pl['funds'] -= 2000
                pl['students'].append({'name': f"学生{len(pl['students'])+1}", 'type': 'Master', 'skill': 50, 'mood': 80})
                st.rerun()
        
        with st.container(border=True):
            st.write("**博士后**")
            st.caption("强力，由于要评职称所以很拼。")
            if st.button("招募 (花费 ¥10000/月)"):
                if pl['funds'] >= 10000:
                    pl['funds'] -= 10000
                    pl['students'].append({'name': f"博后{len(pl['students'])+1}", 'type': 'PostDoc', 'skill': 90, 'mood': 60})
                    st.rerun()
                else: st.error("养不起博后")

# ==========================================
# PAGE 2: ⚡ 交互式求解器 (Solver)
# ==========================================
@st.fragment # 局部刷新黑科技
def page_solver():
    st.title("⚡ 交互式求解器控制台")
    
    sv = st.session_state.solver
    pl = st.session_state.player
    
    # 1. 可视化监控区
    col_chart, col_ctrl = st.columns([3, 1])
    
    with col_chart:
        # 绘制实时残差
        fig = go.Figure()
        fig.add_trace(go.Scatter(y=sv['residuals'], mode='lines', name='Residual', line=dict(color='#00ff00', width=2)))
        fig.update_layout(
            title=f"Residual Monitor (Progress: {int(sv['progress'])}%)",
            template="plotly_dark",
            height=350,
            yaxis_range=[-10, 10],
            xaxis_title="Iterations"
        )
        st.plotly_chart(fig, use_container_width=True)
        
        # 滚动日志
        log_text = "\n".join(sv['logs'][:6])
        st.code(log_text, language="bash")

    with col_ctrl:
        st.subheader("🎛️ 参数调节")
        
        # 核心玩法：玩家调节这两个参数
        new_cfl = st.slider("CFL Number (速度)", 0.1, 5.0, sv['cfl'], 0.1, help="越大越快，但容易炸")
        new_urf = st.slider("Relaxation (稳定性)", 0.1, 1.0, sv['urf'], 0.1, help="越小越稳，但收敛慢")
        
        sv['cfl'] = new_cfl
        sv['urf'] = new_urf
        
        # 速度基准
        base_speed = 1.0
        if pl['hardware'] == 'Workstation': base_speed = 2.0
        elif pl['hardware'] == 'HPC Cluster': base_speed = 5.0
        
        st.metric("当前算力倍率", f"x{base_speed}")
        
        # 炸机概率计算
        # 逻辑：CFL * (1-URF) 越大，风险越高
        risk = (sv['cfl'] * sv['cfl']) * (1.1 - sv['urf']) * 0.05
        st.progress(min(1.0, risk), text=f"当前崩溃风险: {int(risk*100)}%")

        # 操作按钮
        if sv['diverged']:
            st.error("❌ DIVERGED!")
            if st.button("重置求解器"):
                sv['residuals'] = [-1.0]
                sv['progress'] = 0
                sv['diverged'] = False
                sv['logs'] = ["Reset complete."]
                st.rerun()
        
        elif sv['progress'] >= 100:
            st.success("✅ 收敛完成")
            if st.button("提取数据"):
                pl['inventory_data'].append({'quality': random.randint(60, 100), 'type': 'RANS Result'})
                sv['progress'] = 0
                sv['residuals'] = [-1.0]
                st.toast("数据已保存到论文工厂！")
                st.rerun()
        else:
            if st.button("🔥 迭代一步 (Run Step)"):
                # 模拟单步计算
                time.sleep(0.1) # 假装在算
                
                # 1. 判定发散
                if random.random() < risk:
                    sv['diverged'] = True
                    sv['residuals'].append(10.0)
                    add_solver_log("ERROR: Floating point exception!")
                    st.rerun()
                    return

                # 2. 正常计算
                sv['progress'] += (sv['cfl'] * base_speed * 0.5)
                
                # 3. 残差更新
                last_res = sv['residuals'][-1]
                # 核心公式：残差下降 = URF影响 + 随机波动
                drop = -0.1 * sv['urf']
                noise = random.uniform(-0.5, 0.5) * sv['cfl'] * 0.1
                new_res = max(-9, last_res + drop + noise)
                
                sv['residuals'].append(new_res)
                add_solver_log(f"Iter: {len(sv['residuals'])} | Res: {new_res:.4f}")
                st.rerun()

# ==========================================
# PAGE 3: 📝 论文工厂 (Crafting)
# ==========================================
def page_paper():
    st.title("📝 论文组装工厂")
    pl = st.session_state.player
    
    col1, col2 = st.columns([1, 2])
    
    with col1:
        st.subheader("📂 你的素材库")
        st.info(f"拥有数据集: {len(pl['inventory_data'])} 个")
        
        # 显示持有的数据
        if not pl['inventory_data']:
            st.warning("暂无数据，请去【求解器】计算。")
        else:
            st.write("选择 3 个素材合成论文：")
            selected_indices = []
            for i, data in enumerate(pl['inventory_data']):
                if st.checkbox(f"数据 #{i+1} (质量: {data['quality']})", key=f"data_{i}"):
                    selected_indices.append(data)
            
            if len(selected_indices) == 3:
                if st.button("✨ 合成论文 (Craft Paper)"):
                    # 计算总质量
                    total_quality = sum([d['quality'] for d in selected_indices])
                    # 消耗数据
                    pl['inventory_data'] = [d for d in pl['inventory_data'] if d not in selected_indices]
                    # 生成待投稿论文
                    st.session_state.draft_paper = total_quality
                    st.success(f"论文草稿完成！综合评分: {total_quality}")
                    st.rerun()
            elif len(selected_indices) > 3:
                st.error("最多选择 3 个素材！")

    with col2:
        st.subheader("📤 投稿中心")
        if 'draft_paper' in st.session_state:
            score = st.session_state.draft_paper
            st.markdown(f"""
            <div class='game-card'>
                <h3>📄 待投稿论文</h3>
                <p>质量评分: <b>{score}</b> / 300</p>
                <p>只有评分足够高，才能在答辩中存活。</p>
            </div>
            """, unsafe_allow_html=True)
            
            st.write("选择目标期刊：")
            c1, c2, c3 = st.columns(3)
            if c1.button("J. Fluid Mech. (Top)"):
                start_battle("JFM", score, 200) # 难度阈值 200
            if c2.button("Ocean Eng. (Q1)"):
                start_battle("OE", score, 150)
            if c3.button("水刊 (Open Access)"):
                start_battle("OA", score, 50)
        else:
            st.info("请先左侧合成论文。")

def start_battle(journal, score, difficulty):
    st.session_state.battle['active'] = True
    st.session_state.battle['journal'] = journal
    # 玩家血量 = 论文质量
    st.session_state.battle['player_hp'] = score
    # 审稿人血量 = 期刊难度
    st.session_state.battle['reviewer_hp'] = difficulty
    st.session_state.battle['turn_log'] = ["战斗开始！Reviewer #2 正在阅读你的摘要..."]
    # 删除草稿
    del st.session_state.draft_paper

# ==========================================
# PAGE 4: ⚔️ 学术答辩 (Battle)
# ==========================================
def page_battle():
    st.title("⚔️ Peer Review 战场")
    
    bt = st.session_state.battle
    
    if not bt['active']:
        st.info("当前没有进行中的审稿流程。请去【论文工厂】投稿。")
        return

    # 1. 战场显示
    c1, c2 = st.columns(2)
    with c1:
        st.markdown(f"### 🧑‍🎓 你的论文 (HP: {bt['player_hp']})")
        st.progress(min(1.0, max(0.0, bt['player_hp'] / 300)), text="Argument Strength")
    
    with c2:
        st.markdown(f"### 👹 Reviewer #2 (HP: {bt['reviewer_hp']})")
        st.progress(min(1.0, max(0.0, bt['reviewer_hp'] / 300)), text="Stubbornness")

    st.divider()
    
    # 2. 战斗日志
    st.subheader("📜 审稿记录")
    log_box = st.container(height=200)
    for log in bt['turn_log']:
        log_box.write(log)

    # 3. 技能栏
    st.subheader("💬 选择回复策略")
    
    if bt['player_hp'] <= 0:
        st.error("FAILED: 你的论文被拒稿了。")
        if st.button("接受现实 (离开)"):
            bt['active'] = False
            st.rerun()
    elif bt['reviewer_hp'] <= 0:
        st.balloons()
        st.success("ACCEPTED: 恭喜！论文被录用！")
        if st.button("支付版面费并庆祝"):
            bt['active'] = False
            st.session_state.player['reputation'] += 50
            st.session_state.player['funds'] += 5000 # 奖励
            st.rerun()
    else:
        bc1, bc2, bc3 = st.columns(3)
        
        # 技能 1: 引用大牛 (攻击)
        if bc1.button("📚 引用大牛文献"):
            dmg = random.randint(20, 50)
            bt['reviewer_hp'] -= dmg
            bt['turn_log'].append(f"你: 引用了 Batchelor (1967) 的经典理论。造成 {dmg} 点说服力伤害。")
            enemy_turn()
            st.rerun()
            
        # 技能 2: 补实验 (回血)
        if bc2.button("🧪 补充实验数据"):
            heal = random.randint(30, 60)
            bt['player_hp'] += heal
            st.session_state.player['funds'] -= 1000 # 费钱
            bt['turn_log'].append(f"你: 连夜补了实验对比。论文质量恢复 {heal} 点。")
            enemy_turn()
            st.rerun()
            
        # 技能 3: 承认误差 (赌博)
        if bc3.button("🙏 承认是误差"):
            if random.random() < 0.5:
                dmg = 100
                bt['reviewer_hp'] -= dmg
                bt['turn_log'].append("你: 诚恳地承认了不足。审稿人被打动了！造成 100 点伤害。")
            else:
                self_dmg = 50
                bt['player_hp'] -= self_dmg
                bt['turn_log'].append("你: 承认不足。审稿人认为这无法接受！你受到 50 点伤害。")
            enemy_turn()
            st.rerun()

def enemy_turn():
    bt = st.session_state.battle
    if bt['reviewer_hp'] > 0:
        dmg = random.randint(15, 40)
        reasons = [
            "质疑你的网格无关性。",
            "认为湍流模型选用不当。",
            "发现你有个单词拼错了。",
            "表示创新点不足。"
        ]
        msg = random.choice(reasons)
        bt['player_hp'] -= dmg
        bt['turn_log'].append(f"👹 Reviewer #2: {msg} (受到 {dmg} 点打击)")

# ==========================================
# 主导航栏
# ==========================================
st.sidebar.title("🎓 学术大亨 V7.0")
st.sidebar.info(f"第 {st.session_state.player['day']} 天")

# 页面导航
page = st.sidebar.radio("导航", ["🏢 实验室运营", "⚡ 交互求解器", "📝 论文工厂", "⚔️ 学术答辩"])

if page == "🏢 实验室运营":
    page_lab()
elif page == "⚡ 交互求解器":
    page_solver()
elif page == "📝 论文工厂":
    page_paper()
elif page == "⚔️ 学术答辩":
    page_battle()

# 侧边栏底部
st.sidebar.markdown("---")
if st.sidebar.button("💾 保存进度 (假装)"):
    st.toast("进度已保存！")
if st.sidebar.button("💀 删档重开"):
    st.session_state.clear()
    st.rerun()
