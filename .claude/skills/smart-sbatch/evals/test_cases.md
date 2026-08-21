# Skill Evaluation Test Cases

Use these to sanity-check whether the skill routes jobs correctly.

## Should trigger

1. "帮我写一个 sbatch，训练大模型，private-teodoro-gpu 和 shared-gpu 怎么选？"
2. "这个任务只跑 3 小时，但 private 可能排队 1 天，应该交到哪里？"
3. "private 只剩两张 3090，我的训练 4 卡才比较快，能不能用 shared 分段跑？"
4. "private 下周维护，不能提交 7 天，但我的任务只要 2 天，帮我改 time。"
5. "这是 CPU-only 数据预处理命令，要跑 5 天，不需要 GPU，帮我写 sbatch。"
6. "训练能 checkpoint，shared-gpu 只有 12h，怎么写自动保存和续跑？"
7. "我想避免 3080，因为大模型至少要 20GB 显存。"
8. "gpu050 能不能用来训练？"

## Should not trigger

1. "解释一下 Python 的 argparse 怎么用。"
2. "帮我写一封英文邮件给导师。"
3. "这个 Dockerfile 怎么减小镜像体积？" unless the Dockerfile is specifically for Teodoro Slurm submission.
4. "CUDA out of memory 怎么 debug？" unless the user asks for Teodoro partition/node selection.
5. "帮我总结这篇论文。"

## Expected behavior checks

- CPU-only commands route to `private-teodoro-gpu` with 0 GPUs.
- Large-model GPU jobs exclude RTX 3080 nodes by default.
- 7-day walltime is not hardcoded when maintenance/reservations shorten the available window.
- Short jobs prefer shared when private queue wait is longer than the job itself.
- Long non-checkpointable jobs prefer private.
- Long checkpointable jobs can use shared in 12h chunks when private is slow or under-provisioned.
