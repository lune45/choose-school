# 数据库检索员记忆

身份：数据库检索员（负责联网检索学校/项目信息并提交管理员审批）

最后更新：2026-03-03 19:22:34

## 长期记忆策略
- 指令：优先抓取官网可验证信息，补全项目时长与选课清单，保留来源链接，无法确定则标注估算。
- 排名来源优先级：QS > USNEWS > TIMES

## 长期优先目标
- 暂无

## 今日待搜（2026-03-03）
- Carnegie Mellon University · MS in Computer Science
- Imperial College London · MSc Computing
- The University of Melbourne · Master of Information Technology
- University of Southern California · MS in Applied Data Science
- University of Manchester · MSc Advanced Computer Science
- Monash University · Master of Data Science
- Binus University · Master in Computer Science

## 今日已搜（2026-03-03）
- Northeastern University · MS in Information Systems

## 自动重试队列
- Imperial College London · MSc Computing | 次数:2 | 下次:2026-03-03T20:21:37.835316 | 原因:联网搜索无结果
- Carnegie Mellon University · MS in Computer Science | 次数:2 | 下次:2026-03-03T20:21:46.993566 | 原因:联网搜索无结果
- The University of Melbourne · Master of Information Technology | 次数:2 | 下次:2026-03-03T20:21:56.420707 | 原因:联网搜索无结果
- University of Southern California · MS in Applied Data Science | 次数:2 | 下次:2026-03-03T20:22:05.611393 | 原因:联网搜索无结果
- University of Manchester · MSc Advanced Computer Science | 次数:2 | 下次:2026-03-03T20:22:14.935807 | 原因:联网搜索无结果
- Monash University · Master of Data Science | 次数:2 | 下次:2026-03-03T20:22:24.952295 | 原因:联网搜索无结果
- Binus University · Master in Computer Science | 次数:2 | 下次:2026-03-03T20:22:34.960901 | 原因:联网搜索无结果

## 最近失败原因
- 2026-03-03T17:41:52.650435 | Imperial College London · MSc Computing | 联网搜索无结果
- 2026-03-03T17:42:01.911217 | Carnegie Mellon University · MS in Computer Science | 联网搜索无结果
- 2026-03-03T17:42:10.575651 | The University of Melbourne · Master of Information Technology | 联网搜索无结果
- 2026-03-03T17:42:19.225088 | University of Southern California · MS in Applied Data Science | 联网搜索无结果
- 2026-03-03T17:42:28.085311 | University of Manchester · MSc Advanced Computer Science | 联网搜索无结果
- 2026-03-03T17:42:36.941133 | Monash University · Master of Data Science | 联网搜索无结果
- 2026-03-03T17:44:53.634796 | Binus University · Master in Computer Science | 联网搜索无结果
- 2026-03-03T19:21:37.835347 | Imperial College London · MSc Computing | 联网搜索无结果
- 2026-03-03T19:21:46.993589 | Carnegie Mellon University · MS in Computer Science | 联网搜索无结果
- 2026-03-03T19:21:56.420729 | The University of Melbourne · Master of Information Technology | 联网搜索无结果
- 2026-03-03T19:22:05.611418 | University of Southern California · MS in Applied Data Science | 联网搜索无结果
- 2026-03-03T19:22:14.935833 | University of Manchester · MSc Advanced Computer Science | 联网搜索无结果
- 2026-03-03T19:22:24.952323 | Monash University · Master of Data Science | 联网搜索无结果
- 2026-03-03T19:22:34.960930 | Binus University · Master in Computer Science | 联网搜索无结果

## 运行日志
- 初始化
- [16:36:50] 开始检索：country=美国 major=CS limit=1，候选1个
- [16:36:54] 检索完成：新增待审批0条，跳过1条
- [17:41:43] 开始检索：ranking=QS / USNEWS / TIMES country=全部 major=全部 limit=10，候选8个（重试0）
- [17:44:53] 检索完成：新增待审批1条，跳过7条，重试队列7条
- [19:21:28] 开始检索：ranking=QS / USNEWS / TIMES country=全部 major=全部 limit=5，候选7个（重试7）
- [19:22:34] 检索完成：新增待审批0条，跳过7条，重试队列7条

<!-- MEMORY_STATE_START -->
```json
{
  "identity": "数据库检索员",
  "long_term_instruction": "优先抓取官网可验证信息，补全项目时长与选课清单，保留来源链接，无法确定则标注估算。",
  "ranking_sources": [
    "qs",
    "usnews",
    "times"
  ],
  "priority_targets": [],
  "today": "2026-03-03",
  "todo": [
    "Carnegie Mellon University · MS in Computer Science",
    "Imperial College London · MSc Computing",
    "The University of Melbourne · Master of Information Technology",
    "University of Southern California · MS in Applied Data Science",
    "University of Manchester · MSc Advanced Computer Science",
    "Monash University · Master of Data Science",
    "Binus University · Master in Computer Science"
  ],
  "done": [
    "Northeastern University · MS in Information Systems"
  ],
  "logs": [
    "初始化",
    "[16:36:50] 开始检索：country=美国 major=CS limit=1，候选1个",
    "[16:36:54] 检索完成：新增待审批0条，跳过1条",
    "[17:41:43] 开始检索：ranking=QS / USNEWS / TIMES country=全部 major=全部 limit=10，候选8个（重试0）",
    "[17:44:53] 检索完成：新增待审批1条，跳过7条，重试队列7条",
    "[19:21:28] 开始检索：ranking=QS / USNEWS / TIMES country=全部 major=全部 limit=5，候选7个（重试7）",
    "[19:22:34] 检索完成：新增待审批0条，跳过7条，重试队列7条"
  ],
  "retry_queue": [
    {
      "school_program_id": 6,
      "target": "Imperial College London · MSc Computing",
      "attempts": 2,
      "last_reason": "联网搜索无结果",
      "updated_at": "2026-03-03T19:21:37.835316",
      "next_retry_at": "2026-03-03T20:21:37.835316"
    },
    {
      "school_program_id": 1,
      "target": "Carnegie Mellon University · MS in Computer Science",
      "attempts": 2,
      "last_reason": "联网搜索无结果",
      "updated_at": "2026-03-03T19:21:46.993566",
      "next_retry_at": "2026-03-03T20:21:46.993566"
    },
    {
      "school_program_id": 4,
      "target": "The University of Melbourne · Master of Information Technology",
      "attempts": 2,
      "last_reason": "联网搜索无结果",
      "updated_at": "2026-03-03T19:21:56.420707",
      "next_retry_at": "2026-03-03T20:21:56.420707"
    },
    {
      "school_program_id": 3,
      "target": "University of Southern California · MS in Applied Data Science",
      "attempts": 2,
      "last_reason": "联网搜索无结果",
      "updated_at": "2026-03-03T19:22:05.611393",
      "next_retry_at": "2026-03-03T20:22:05.611393"
    },
    {
      "school_program_id": 7,
      "target": "University of Manchester · MSc Advanced Computer Science",
      "attempts": 2,
      "last_reason": "联网搜索无结果",
      "updated_at": "2026-03-03T19:22:14.935807",
      "next_retry_at": "2026-03-03T20:22:14.935807"
    },
    {
      "school_program_id": 5,
      "target": "Monash University · Master of Data Science",
      "attempts": 2,
      "last_reason": "联网搜索无结果",
      "updated_at": "2026-03-03T19:22:24.952295",
      "next_retry_at": "2026-03-03T20:22:24.952295"
    },
    {
      "school_program_id": 8,
      "target": "Binus University · Master in Computer Science",
      "attempts": 2,
      "last_reason": "联网搜索无结果",
      "updated_at": "2026-03-03T19:22:34.960901",
      "next_retry_at": "2026-03-03T20:22:34.960901"
    }
  ],
  "failure_history": [
    {
      "time": "2026-03-03T17:41:52.650435",
      "target": "Imperial College London · MSc Computing",
      "reason": "联网搜索无结果"
    },
    {
      "time": "2026-03-03T17:42:01.911217",
      "target": "Carnegie Mellon University · MS in Computer Science",
      "reason": "联网搜索无结果"
    },
    {
      "time": "2026-03-03T17:42:10.575651",
      "target": "The University of Melbourne · Master of Information Technology",
      "reason": "联网搜索无结果"
    },
    {
      "time": "2026-03-03T17:42:19.225088",
      "target": "University of Southern California · MS in Applied Data Science",
      "reason": "联网搜索无结果"
    },
    {
      "time": "2026-03-03T17:42:28.085311",
      "target": "University of Manchester · MSc Advanced Computer Science",
      "reason": "联网搜索无结果"
    },
    {
      "time": "2026-03-03T17:42:36.941133",
      "target": "Monash University · Master of Data Science",
      "reason": "联网搜索无结果"
    },
    {
      "time": "2026-03-03T17:44:53.634796",
      "target": "Binus University · Master in Computer Science",
      "reason": "联网搜索无结果"
    },
    {
      "time": "2026-03-03T19:21:37.835347",
      "target": "Imperial College London · MSc Computing",
      "reason": "联网搜索无结果"
    },
    {
      "time": "2026-03-03T19:21:46.993589",
      "target": "Carnegie Mellon University · MS in Computer Science",
      "reason": "联网搜索无结果"
    },
    {
      "time": "2026-03-03T19:21:56.420729",
      "target": "The University of Melbourne · Master of Information Technology",
      "reason": "联网搜索无结果"
    },
    {
      "time": "2026-03-03T19:22:05.611418",
      "target": "University of Southern California · MS in Applied Data Science",
      "reason": "联网搜索无结果"
    },
    {
      "time": "2026-03-03T19:22:14.935833",
      "target": "University of Manchester · MSc Advanced Computer Science",
      "reason": "联网搜索无结果"
    },
    {
      "time": "2026-03-03T19:22:24.952323",
      "target": "Monash University · Master of Data Science",
      "reason": "联网搜索无结果"
    },
    {
      "time": "2026-03-03T19:22:34.960930",
      "target": "Binus University · Master in Computer Science",
      "reason": "联网搜索无结果"
    }
  ]
}
```
<!-- MEMORY_STATE_END -->
