import numpy as np


def analyze_index_distribution(indices):
    # Step 1: 将索引排序（确保输入是有序的）
    if not indices:
        return indices
    indices = sorted(indices)

    # Step 2: 找到所有连续区间
    consecutive_groups = []
    current_group = [indices[0]]  # 初始化第一个连续区间

    for i in range(1, len(indices)):
        if indices[i] <= indices[i - 1] + 25:  # 如果当前索引与前一个索引连续
            current_group.append(indices[i])
        else:
            # 当前索引不连续时，保存当前组并开始新组
            consecutive_groups.append(current_group)
            current_group = [indices[i]]

    # 别忘了保存最后一个组
    consecutive_groups.append(current_group)

    # Step 3: 计算每个连续区间的长度
    lengths = [len(group) for group in consecutive_groups]

    # Step 4: 统计指标
    max_length = max(lengths)  # 最大连续区间长度
    avg_length = np.mean(lengths)  # 平均连续区间长度
    var_length = np.var(lengths)  # 连续区间长度的方差

    result = {
        "max_consecutive_length": max_length,
        "avg_consecutive_length": avg_length,
        "var_consecutive_length": var_length,
        "consecutive_groups": consecutive_groups,  # 所有连续区间
        "lengths": lengths  # 每个区间的长度
    }

    # 输出结果
    print("最大连续区间长度:", result["max_consecutive_length"])
    print("平均连续区间长度:", result["avg_consecutive_length"])
    print("连续区间长度方差:", result["var_consecutive_length"])
    print("所有连续区间:", result["consecutive_groups"])
    print("每个区间的长度:", result["lengths"])
    # Step 5: 返回结果
    return result


if __name__ == '__main__':
    pass
