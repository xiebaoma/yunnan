# 云南省企业就业失业数据采集系统（最简可演示版）

一个用于软件项目管理课程答辩展示的最小可用系统，基于 Flask + SQLite，实现完整流程：

`登录 -> 企业填报 -> 审核 -> 统计 -> Agent辅助分析`

## 1. 技术栈
- 后端：Flask
- 前端：Jinja2 + HTML + CSS
- 数据库：SQLite（`data.db`）
- ORM：未使用，直接使用 `sqlite3`

## 2. 项目结构
```text
employ-system/
├── app.py                  # 主程序（路由、业务逻辑、Agent规则）
├── init_db.py              # 初始化数据库脚本
├── seed_demo_data.py       # 可选：插入演示数据
├── requirements.txt        # 依赖
├── README.md               # 说明文档
├── data.db                 # SQLite数据库（初始化后生成）
├── static/
│   └── style.css           # 简单样式
└── templates/
    ├── base.html           # 公共布局
    ├── login.html          # 登录页
    ├── enterprise_form.html# 企业填报页
    ├── review_list.html    # 审核列表页
    ├── review_detail.html  # 审核详情页
    ├── stats.html          # 统计页
    └── agent.html          # Agent分析页
```

## 3. 安装依赖
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## 4. 初始化数据库
```bash
python init_db.py
```

执行后会创建 `data.db`，并写入测试账号。

## 5. 启动系统
```bash
python app.py
```

默认访问地址：
- [http://127.0.0.1:5000](http://127.0.0.1:5000)

## 6. 测试账号
- 企业用户：`enterprise1 / 123456`
- 审核员：`reviewer1 / 123456`
- 管理员：`admin1 / 123456`

## 7. 页面说明
1. 登录页：输入账号密码登录，按角色跳转
2. 企业填报页：企业用户填写就业失业数据并提交
3. 审核列表页：审核员/管理员查看全部数据
4. 审核详情页：执行“通过/退回”，填写审核意见
5. 统计页：查看总数、通过数、待审核数、按地区和周期统计
6. Agent分析页：选择一条数据，自动给出异常提示和审核建议

## 8. Agent规则（模拟版）
系统不调用外部大模型，使用规则模拟 Agent：
- 若 `离职人数 > 在职人数 * 0.5`：提示“离职率过高，疑似异常”
- 若 `招聘需求人数 > max(20, 在职人数 * 0.8)`：提示“招聘需求波动较大”
- 若 `新增就业人数 <= 3` 且 `离职人数 <= 3` 且 `招聘需求 <= 10`：提示“数据基本正常”
- 否则：提示“未发现明显异常，建议人工复核”

## 9. 可选：插入初始演示数据
如果希望快速看到审核和统计效果，可执行：
```bash
python seed_demo_data.py
```

## 10. 推荐课堂演示流程
1. 使用企业账号登录
2. 在企业填报页提交一条记录
3. 退出后使用审核员账号登录
4. 在审核列表进入详情，对记录通过/退回
5. 打开统计页查看汇总变化
6. 打开 Agent 分析页查看自动分析和建议

