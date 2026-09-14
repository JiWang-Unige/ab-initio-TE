# 固定 D 同输入 CPU/GPU 测速

CPU 作业 12696616_[0–2]、GPU 作业 12708296_[0–2] 均完成。每格同一既定首个 1 MiB 区域、模型、校准、batch=12、256 个 4096 bp 窗口；每个节点分配4 CPU。

|物种|CPU第二次前向秒|GPU第二次前向秒|CPU/GPU耗时比|GPU|
|---|---:|---:|---:|---|
|platypus|758.310|31.017|24.45|NVIDIA TITAN X (Pascal)|
|sea_urchin|754.029|30.795|24.49|NVIDIA TITAN X (Pascal)|
|c_briggsae|732.969|34.364|21.33|Tesla P100-PCIE-12GB|

这只比较当前模型同一输入的前向路径：包括分词、模型计算和bp投影；模型加载另计，不包含输入准备、最终注释写盘、library discovery 或传统方法后处理。旧字段 cold 表示模型加载后的第一次前向，不是操作系统冷缓存。各格只跑第一次和第二次前向，没有用不同硬件的数值推断全基因组速度，也没有对CPU/GPU完整概率做数值等价判定。

CPU三格均在cpu203，Slurm node features为E5-2680V4,V6；来源为本轮sacct与scontrol回查。旧CPU timing.json没有自动采集hardware字段，因此不把它写成当时记录的lscpu型号。GPU两格使用TITAN X (Pascal)，一格P100；不能把三格混合成硬件无关的GPU速度。原始时间字段保留在results/{species}/{cpu,gpu}-timing.json。
