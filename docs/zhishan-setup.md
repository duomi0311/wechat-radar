# 知山 · 法律公众号阅读与知识卡

## 使用ChatGPT/Codex整理，不配置AI API

在可访问微信公众平台的电脑上使用本分支。Windows项目目录建议为
`D:\多米的codex\wechat-radar`，虚拟环境也放在项目目录内。

```bash
python -m pip install -r requirements.txt
python collect_articles.py --login
python collect_articles.py --smoke
python collect_articles.py
```

登录二维码在项目的 `login_temp/wechat_qr.png`，若未自动打开可手动查看扫码。
需要使用有微信公众号后台权限的微信账号确认。扫码凭据保存在项目的 `token.json`，
不要上传此登录文件。上述采集入口无需AI密钥或推送渠道，不会发邮件或消息。

`--smoke`依次检查所有指定账号近14天的文章元数据，不拉正文。
通过后完整采集默认近24小时文章；结果保存为 `collected_articles/articles-时间.json`。
将该JSON交给ChatGPT/Codex即可整理文字知识卡，无需在项目内调用AI API。
项目不将JSON自动送进ChatGPT；每日自动采集、持久化存储及定时整理尚待配置。

当前云端直接请求微信登录接口返回HTTP 405，未能取得二维码；电脑端登录仍需实际验证。
这不代表你已经登录失败，也不能据此断定本机一定可用。

## 已配置

监控名称：山东高法、上海一中法院、天同诉讼圈、icourt法秀、北大法宝、高杉LEGAL。
名称保留用户输入，扫码后应逐一核对；忽略大小写和空格，但不会选择不同名称的搜索结果。

筛选方向：民商事裁判规则、证据、程序、保全执行、诉讼方法。
默认每次读取最近24小时文章；按原有日程北京时间约09:07运行，10:33为补漏窗口。
GitHub可能排队，时间不保证精确。部署前可另定生成时间。

知识卡只基于达到推荐阈值的文章生成，每篇最多一张，不强行为通知或广告制卡。
字段为核心知识、适用场景、条件与例外、实务核对、待核实事项、原文依据与链接。
逐字核对摘录只能检查引用是否存在，不能证明其他字段正确；所有卡片待人工复核。
正文超过20,000字符会标记只阅读了截取部分。图片卡暂未实现。

## 启用前准备

在仓库 Settings → Secrets and variables → Actions 配置：

- `AI_PROVIDER`：使用兼容接口时为 `openai-compatible`。
- `AI_API_KEY`、`AI_BASE_URL`、`AI_MODEL`：填写所选服务商的有效配置。
- `WECHAT_TOKEN_JSON`：在可信电脑运行 `python3 main.py --login`，扫码完成后将生成的
  `token.json` 全文保存为这个 Secret。需要拥有可登录的微信公众号后台。
- 至少一种推送渠道：当前工作流接入 `FEISHU_WEBHOOK`，或邮件所需的
  `EMAIL_USER`、`EMAIL_PASSWORD`、`EMAIL_TO`。其他渠道需要另外接入工作流。

密钥、Cookie和登录文件只放到Secret，不提交到代码或聊天中。
外部AI服务会接收所选文章的正文用于整理。配置服务前了解其计费与数据处理方式。

## 最小验证顺序

1. 先安装 `requirements.txt`，运行 `python3 health_check.py`。
2. 扫码后逐号检查：`python3 health_check.py --wechat-smoke --account "山东高法"`，
   再替换为其余五个名称。检查只拉取文章元数据，不调用AI、不推送。
3. 合入修改后，在 Actions → wechat-radar daily digest → Run workflow，先选 `mode=smoke`。
4. smoke通过后选 `mode=dry_run`：会抓正文、调用AI评分与制卡，有AI用量，但不推送。
5. 运行结束后打开该次任务的 Artifacts，下载 `zhishan-knowledge-cards-运行编号`。
   文件包含 Markdown与JSON，默认保留30天；需要长期保存时自行下载。
6. 验证内容后再启用定时执行。启用时将通过已配置的渠道发送原有文章日报，
   知识卡目前作为Artifacts提供下载，不作为邮件附件或图片发送。

若无推荐文章，会写明本次无知识卡；若登录、API或制卡校验失败，任务会报失败。
当前没有验证真实公众号登录、六个账号的身份、AI调用或消息投递。
登录过期时更新 `WECHAT_TOKEN_JSON`，先重新运行smoke，勿用改代码代替更新凭据。

## 离线验证

```bash
python3 -m py_compile main.py filter.py fetcher.py knowledge_cards.py
python3 -m unittest discover -s tests -v
```
